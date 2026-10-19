"""Summarise every tracked MLflow run (incl. nested tuning runs).

    python scripts/experiment_summary.py

Writes reports/experiment_runs.csv and
reports/figures/experiment_tracking_summary.png.
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mlflow  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from heart_risk import config  # noqa: E402

COLORS = {"logistic_regression": "#1f6f8b", "random_forest": "#e8505b",
          "gradient_boosting": "#f9a826"}


def load_runs():
    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
    exp = mlflow.get_experiment_by_name(config.MLFLOW_EXPERIMENT)
    runs = mlflow.search_runs([exp.experiment_id])
    parents = runs[runs["tags.mlflow.parentRunId"].isna()]
    family = dict(zip(parents["run_id"], parents["tags.mlflow.runName"]))
    children = runs[runs["tags.mlflow.parentRunId"].notna()].copy()
    children["family"] = children["tags.mlflow.parentRunId"].map(family)
    return runs, children


def main():
    runs, children = load_runs()
    cols = ["family", "tags.mlflow.runName", "metrics.cv_roc_auc",
            "metrics.cv_roc_auc_std", "metrics.cv_accuracy",
            "metrics.cv_recall"] + [c for c in children.columns
                                    if c.startswith("params.")]
    table = children[cols].sort_values("metrics.cv_roc_auc", ascending=False)
    out_csv = config.REPORTS_DIR / "experiment_runs.csv"
    table.to_csv(out_csv, index=False)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    fams = list(COLORS)
    data = [children.loc[children.family == f, "metrics.cv_roc_auc"]
            for f in fams]
    bp = axes[0].boxplot(data, patch_artist=True, widths=0.5)
    for patch, f in zip(bp["boxes"], fams):
        patch.set_facecolor(COLORS[f])
        patch.set_alpha(0.6)
    for i, d in enumerate(data, start=1):
        axes[0].scatter([i] * len(d), d, s=12, color="black", alpha=0.5)
    axes[0].set_xticks(range(1, 4), [f.replace("_", "\n") for f in fams])
    axes[0].set_ylabel("5-fold CV ROC-AUC")
    axes[0].set_title(f"All {len(children)} tuning runs logged to MLflow")

    lr = children[children.family == "logistic_regression"].copy()
    lr["C"] = lr["params.C"].astype(float)
    for (pen, cw), grp in lr.groupby(["params.penalty",
                                      "params.class_weight"]):
        grp = grp.sort_values("C")
        axes[1].plot(grp["C"], grp["metrics.cv_roc_auc"], marker="o",
                     label=f"{pen}, class_weight={cw}")
    axes[1].set_xscale("log")
    axes[1].set_xlabel("C (inverse regularisation)")
    axes[1].set_ylabel("5-fold CV ROC-AUC")
    axes[1].set_title("Logistic regression tuning curve")
    axes[1].legend(fontsize=7)
    fig.tight_layout()
    out_png = config.FIGURES_DIR / "experiment_tracking_summary.png"
    fig.savefig(out_png, dpi=130)
    print(f"{len(runs)} runs ({len(children)} nested) -> {out_csv}, {out_png}")
    print(table.head(10)[["family", "metrics.cv_roc_auc"]].to_string())


if __name__ == "__main__":
    main()
