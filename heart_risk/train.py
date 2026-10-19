"""Train, tune and compare classifiers with full MLflow tracking.

Usage:
    python -m heart_risk.train            # full grid search
    python -m heart_risk.train --quick    # tiny grids (CI smoke run)

Model selection rule: the champion is the family with the best *mean CV
ROC-AUC on the training split*. The held-out test split is only used to
report final, unbiased metrics - never to pick the model.
"""

import argparse
import json
import logging
import shutil
from datetime import datetime, timezone

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from mlflow.models import infer_signature
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import (GridSearchCV, StratifiedKFold,
                                     train_test_split)

from heart_risk import __version__, config, data, evaluate
from heart_risk.features import build_pipeline, transformed_feature_names

log = logging.getLogger("heart_risk.train")

SCORING = ["accuracy", "precision", "recall", "f1", "roc_auc"]

CANDIDATES = {
    "logistic_regression": {
        "estimator": LogisticRegression(max_iter=5000, solver="liblinear",
                                        random_state=config.RANDOM_STATE),
        "grid": {
            "model__C": [0.01, 0.03, 0.1, 0.3, 1.0, 3.0],
            "model__penalty": ["l1", "l2"],
            "model__class_weight": [None, "balanced"],
        },
        "quick_grid": {"model__C": [0.1, 1.0]},
    },
    "random_forest": {
        "estimator": RandomForestClassifier(random_state=config.RANDOM_STATE,
                                            n_jobs=-1),
        "grid": {
            "model__n_estimators": [300],
            "model__max_depth": [3, 5, 8, None],
            "model__min_samples_leaf": [1, 4, 8],
            "model__max_features": ["sqrt", 0.5],
        },
        "quick_grid": {"model__n_estimators": [50], "model__max_depth": [4]},
    },
    "gradient_boosting": {
        "estimator": GradientBoostingClassifier(
            random_state=config.RANDOM_STATE),
        "grid": {
            "model__n_estimators": [100, 200],
            "model__learning_rate": [0.03, 0.1],
            "model__max_depth": [2, 3],
            "model__subsample": [0.7, 1.0],
        },
        "quick_grid": {"model__n_estimators": [50]},
    },
}


def _strip(params: dict) -> dict:
    return {k.replace("model__", ""): v for k, v in params.items()}


def _importances(pipe):
    model = pipe.named_steps["model"]
    if hasattr(model, "coef_"):
        return model.coef_[0], "coefficient (standardised scale)"
    return model.feature_importances_, "impurity importance"


def run_family(name, spec, X_train, y_train, X_test, y_test, cv, quick):
    grid = spec["quick_grid"] if quick else spec["grid"]
    search = GridSearchCV(build_pipeline(spec["estimator"]), grid,
                          scoring=SCORING, refit="roc_auc", cv=cv,
                          n_jobs=-1, return_train_score=False)

    with mlflow.start_run(run_name=name) as parent:
        mlflow.set_tags({"model_family": name, "stage": "tuning",
                         "package_version": __version__})
        search.fit(X_train, y_train)
        res = pd.DataFrame(search.cv_results_)

        # One nested child run per hyper-parameter combination.
        for _, row in res.iterrows():
            with mlflow.start_run(run_name=f"{name}-cfg{int(row.name)}",
                                  nested=True):
                mlflow.log_params(_strip(row["params"]))
                mlflow.log_metrics({
                    **{f"cv_{m}": row[f"mean_test_{m}"] for m in SCORING},
                    **{f"cv_{m}_std": row[f"std_test_{m}"] for m in SCORING},
                    "rank_roc_auc": float(row["rank_test_roc_auc"]),
                })

        best = search.best_estimator_
        bi = search.best_index_
        cv_best = {f"cv_{m}": res.loc[bi, f"mean_test_{m}"] for m in SCORING}
        y_prob = best.predict_proba(X_test)[:, 1]
        test = {f"test_{k}": v for k, v in
                evaluate.classification_metrics(y_test, y_prob).items()}

        mlflow.log_params({"cv_folds": cv.get_n_splits(),
                           "n_grid_points": len(res),
                           **_strip(search.best_params_)})
        mlflow.log_metrics({**cv_best, **test})

        fig_dir = config.FIGURES_DIR / name
        pretty = name.replace("_", " ").title()
        names = transformed_feature_names(best)
        values, label = _importances(best)
        plots = [
            evaluate.plot_confusion(y_test, y_prob, f"{pretty} - test",
                                    fig_dir / "confusion_matrix.png"),
            evaluate.plot_roc(y_test, y_prob, f"{pretty} - ROC (test)",
                              fig_dir / "roc_curve.png"),
            evaluate.plot_pr(y_test, y_prob, f"{pretty} - PR (test)",
                             fig_dir / "pr_curve.png"),
            evaluate.plot_feature_importance(
                names, values, f"{pretty} - {label}",
                fig_dir / "feature_importance.png"),
        ]
        for p in plots:
            mlflow.log_artifact(str(p), artifact_path="plots")
        cv_csv = fig_dir / "cv_results.csv"
        res.drop(columns=["params"]).to_csv(cv_csv, index=False)
        mlflow.log_artifact(str(cv_csv), artifact_path="cv")

        sig = infer_signature(X_test, best.predict_proba(X_test))
        mlflow.sklearn.log_model(best, artifact_path="model", signature=sig,
                                 input_example=X_test.head(3))
        log.info("%-20s cv_roc_auc=%.4f test_roc_auc=%.4f best=%s", name,
                 cv_best["cv_roc_auc"], test["test_roc_auc"],
                 _strip(search.best_params_))
        return {"family": name, "run_id": parent.info.run_id,
                "best_params": _strip(search.best_params_),
                "pipeline": best, **cv_best, **test}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true",
                        help="small grids for CI smoke tests")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    df = data.build_clean_dataset()
    X, y = data.split_xy(df)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=config.TEST_SIZE, stratify=y,
        random_state=config.RANDOM_STATE)
    cv = StratifiedKFold(n_splits=config.CV_FOLDS, shuffle=True,
                         random_state=config.RANDOM_STATE)

    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
    mlflow.set_experiment(config.MLFLOW_EXPERIMENT)
    log.info("MLflow tracking URI: %s", config.MLFLOW_TRACKING_URI)

    results = [run_family(n, s, X_train, y_train, X_test, y_test, cv,
                          args.quick) for n, s in CANDIDATES.items()]
    summary = pd.DataFrame(results).set_index("family").drop(
        columns=["pipeline", "best_params", "run_id"])
    champion = max(results, key=lambda r: r["cv_roc_auc"])
    log.info("Champion: %s (cv_roc_auc=%.4f)", champion["family"],
             champion["cv_roc_auc"])

    # ---- package the champion -------------------------------------------
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(champion["pipeline"], config.MODELS_DIR / "heart_model.joblib")
    if config.MLFLOW_MODEL_DIR.exists():
        shutil.rmtree(config.MLFLOW_MODEL_DIR)
    mlflow.sklearn.save_model(
        champion["pipeline"], str(config.MLFLOW_MODEL_DIR),
        signature=infer_signature(X_test,
                                  champion["pipeline"].predict_proba(X_test)),
        input_example=X_test.head(3))

    metadata = {
        "model_name": "heart-disease-risk",
        "model_version": __version__,
        "family": champion["family"],
        "mlflow_run_id": champion["run_id"],
        "best_params": champion["best_params"],
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "features": config.FEATURES,
        "decision_threshold": 0.5,
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "metrics": {k: round(float(v), 4) for k, v in champion.items()
                    if k.startswith(("cv_", "test_"))},
        "quick_mode": args.quick,
    }
    config.MODEL_METADATA_PATH.write_text(json.dumps(metadata, indent=2))

    comparison_png = evaluate.plot_model_comparison(
        summary, config.FIGURES_DIR / "model_comparison.png")
    summary_csv = config.REPORTS_DIR / "model_comparison.csv"
    summary.round(4).to_csv(summary_csv)

    with mlflow.start_run(run_name="champion-selection"):
        mlflow.set_tags({"stage": "selection",
                         "champion": champion["family"],
                         "champion_run_id": champion["run_id"]})
        mlflow.log_metrics({f"champion_{k}": v
                            for k, v in metadata["metrics"].items()})
        for p in (comparison_png, summary_csv, config.MODEL_METADATA_PATH):
            mlflow.log_artifact(str(p))
    print(summary.round(4).to_string())
    return metadata


if __name__ == "__main__":
    main()
