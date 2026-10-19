"""Metrics and evaluation plots (all plots are returned as saved file paths)."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    accuracy_score, average_precision_score, confusion_matrix, f1_score,
    precision_recall_curve, precision_score, recall_score, roc_auc_score,
    roc_curve,
)

PALETTE = {"main": "#1f6f8b", "accent": "#e8505b", "muted": "#99a8b2"}


def classification_metrics(y_true, y_prob, threshold: float = 0.5) -> dict:
    y_pred = (np.asarray(y_prob) >= threshold).astype(int)
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_true, y_prob),
        "avg_precision": average_precision_score(y_true, y_prob),
    }


def plot_confusion(y_true, y_prob, title, path: Path, threshold=0.5) -> Path:
    y_pred = (np.asarray(y_prob) >= threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(4.2, 3.8))
    ax.imshow(cm, cmap="Blues")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=14,
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    ax.set_xticks([0, 1], ["No disease", "Disease"])
    ax.set_yticks([0, 1], ["No disease", "Disease"])
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title(title)
    return _save(fig, path)


def plot_roc(y_true, y_prob, title, path: Path) -> Path:
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    auc = roc_auc_score(y_true, y_prob)
    fig, ax = plt.subplots(figsize=(4.5, 4))
    ax.plot(fpr, tpr, color=PALETTE["main"], lw=2, label=f"AUC = {auc:.3f}")
    ax.plot([0, 1], [0, 1], ls="--", color=PALETTE["muted"])
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title(title)
    ax.legend(loc="lower right")
    return _save(fig, path)


def plot_pr(y_true, y_prob, title, path: Path) -> Path:
    prec, rec, _ = precision_recall_curve(y_true, y_prob)
    ap = average_precision_score(y_true, y_prob)
    fig, ax = plt.subplots(figsize=(4.5, 4))
    ax.plot(rec, prec, color=PALETTE["accent"], lw=2, label=f"AP = {ap:.3f}")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_ylim(0, 1.05)
    ax.set_title(title)
    ax.legend(loc="lower left")
    return _save(fig, path)


def plot_feature_importance(names, values, title, path: Path,
                            top: int = 15) -> Path:
    s = pd.Series(values, index=names)
    s = s.reindex(s.abs().sort_values(ascending=True).index)[-top:]
    colors = [PALETTE["accent"] if v < 0 else PALETTE["main"] for v in s]
    fig, ax = plt.subplots(figsize=(6, 0.32 * len(s) + 1))
    ax.barh(s.index, s.values, color=colors)
    ax.axvline(0, color="black", lw=0.6)
    ax.set_title(title)
    return _save(fig, path)


def plot_model_comparison(summary: pd.DataFrame, path: Path) -> Path:
    """Grouped bars of CV metrics for every model family."""
    metrics = ["accuracy", "precision", "recall", "f1", "roc_auc"]
    x = np.arange(len(metrics))
    width = 0.8 / len(summary)
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = ["#1f6f8b", "#e8505b", "#f9a826", "#5c946e"]
    for i, (name, row) in enumerate(summary.iterrows()):
        ax.bar(x + i * width, [row[f"cv_{m}"] for m in metrics], width,
               label=name, color=colors[i % len(colors)])
    ax.set_xticks(x + width * (len(summary) - 1) / 2, metrics)
    ax.set_ylim(0.6, 1.0)
    ax.set_ylabel("5-fold CV score")
    ax.set_title("Model comparison (cross-validation, training split)")
    ax.legend(loc="lower right", fontsize=8)
    return _save(fig, path)


def _save(fig, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path
