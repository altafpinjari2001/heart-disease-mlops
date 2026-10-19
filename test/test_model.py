import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from heart_risk import config, evaluate
from heart_risk.features import build_pipeline
from heart_risk.predict import predict_records


def _fit(df, est):
    return build_pipeline(est).fit(df[config.FEATURES], df[config.TARGET])


def test_models_learn_signal(synthetic_dataset):
    for est in (LogisticRegression(max_iter=1000),
                RandomForestClassifier(n_estimators=50, random_state=0)):
        pipe = _fit(synthetic_dataset, est)
        prob = pipe.predict_proba(synthetic_dataset[config.FEATURES])[:, 1]
        m = evaluate.classification_metrics(synthetic_dataset[config.TARGET],
                                            prob)
        assert m["roc_auc"] > 0.75


def test_metrics_keys_and_ranges():
    y = np.array([0, 0, 1, 1])
    p = np.array([0.1, 0.6, 0.4, 0.9])
    m = evaluate.classification_metrics(y, p)
    assert set(m) == {"accuracy", "precision", "recall", "f1", "roc_auc",
                      "avg_precision"}
    assert m["accuracy"] == 0.5
    assert m["roc_auc"] == 0.75


def test_predict_records_contract(synthetic_dataset):
    pipe = _fit(synthetic_dataset, LogisticRegression(max_iter=1000))
    record = synthetic_dataset[config.FEATURES].iloc[0].to_dict()
    record.pop("ca")  # missing optional field is imputed
    out = predict_records([record], model=pipe)[0]
    assert out["prediction"] in (0, 1)
    assert 0.5 <= out["confidence"] <= 1.0
    assert 0.0 <= out["risk_probability"] <= 1.0
    assert out["label"] in ("heart_disease", "no_heart_disease")


def test_model_roundtrip_is_deterministic(synthetic_dataset, tmp_path):
    pipe = _fit(synthetic_dataset,
                RandomForestClassifier(n_estimators=30, random_state=1))
    path = tmp_path / "m.joblib"
    joblib.dump(pipe, path)
    X = synthetic_dataset[config.FEATURES]
    assert np.allclose(pipe.predict_proba(X),
                       joblib.load(path).predict_proba(X))


def test_plots_are_written(tmp_path):
    y = np.array([0, 1, 0, 1, 1])
    p = np.array([0.2, 0.7, 0.4, 0.8, 0.3])
    for fn in (evaluate.plot_confusion, evaluate.plot_roc, evaluate.plot_pr):
        path = fn(y, p, "t", tmp_path / f"{fn.__name__}.png")
        assert path.exists() and path.stat().st_size > 0
