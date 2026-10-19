"""Exploratory data analysis figures (used by notebooks/01_eda.ipynb).

    python -m heart_risk.eda     # writes all figures to reports/figures/eda
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

from heart_risk import config, data  # noqa: E402

OUT = config.FIGURES_DIR / "eda"
CLASS_COLORS = {0: "#1f6f8b", 1: "#e8505b"}
CLASS_NAMES = {0: "No disease", 1: "Disease"}

PRETTY = {
    "age": "Age (years)", "trestbps": "Resting BP (mm Hg)",
    "chol": "Serum cholesterol (mg/dl)", "thalach": "Max heart rate",
    "oldpeak": "ST depression (oldpeak)", "ca": "# major vessels (ca)",
    "cp": "Chest pain type", "restecg": "Resting ECG", "slope": "ST slope",
    "thal": "Thalassemia", "sex": "Sex (1 = male)",
    "fbs": "Fasting sugar > 120", "exang": "Exercise angina",
}

CODE_LABELS = {
    "cp": {1: "typical", 2: "atypical", 3: "non-anginal", 4: "asymptomatic"},
    "restecg": {0: "normal", 1: "ST-T abn.", 2: "LV hypertrophy"},
    "slope": {1: "up", 2: "flat", 3: "down"},
    "thal": {3: "normal", 6: "fixed", 7: "reversible"},
    "sex": {0: "female", 1: "male"},
    "fbs": {0: "no", 1: "yes"},
    "exang": {0: "no", 1: "yes"},
}


def _save(fig, name) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def class_balance(df):
    counts = df[config.TARGET].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(4.5, 3.5))
    bars = ax.bar([CLASS_NAMES[i] for i in counts.index], counts.values,
                  color=[CLASS_COLORS[i] for i in counts.index])
    for b, v in zip(bars, counts.values):
        ax.text(b.get_x() + b.get_width() / 2, v + 2,
                f"{v} ({v / counts.sum():.0%})", ha="center")
    ax.set_ylabel("Patients")
    ax.set_title("Target class balance")
    ax.set_ylim(0, counts.max() * 1.15)
    return _save(fig, "01_class_balance.png")


def missing_values(raw):
    miss = raw.isna().sum()
    miss = miss[miss > 0]
    fig, ax = plt.subplots(figsize=(4.5, 2.8))
    ax.barh(miss.index, miss.values, color="#f9a826")
    for i, v in enumerate(miss.values):
        ax.text(v + 0.1, i, str(v), va="center")
    ax.set_xlabel("Missing values ('?' in raw file)")
    ax.set_title(f"Missing data - {len(raw)} rows")
    return _save(fig, "02_missing_values.png")


def continuous_histograms(df):
    cols = config.CONTINUOUS_FEATURES
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.5))
    for ax, col in zip(axes.ravel(), cols):
        for cls in (0, 1):
            sns.histplot(df.loc[df[config.TARGET] == cls, col].dropna(),
                         ax=ax, color=CLASS_COLORS[cls], kde=col != "ca",
                         stat="density", alpha=0.45, label=CLASS_NAMES[cls],
                         discrete=col == "ca")
        ax.set_title(PRETTY[col])
        ax.set_xlabel("")
    axes[0, 0].legend()
    fig.suptitle("Distribution of continuous features by diagnosis", y=1.0)
    return _save(fig, "03_histograms.png")


def correlation_heatmap(df):
    corr = df[config.FEATURES + [config.TARGET]].corr(method="spearman")
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    fig, ax = plt.subplots(figsize=(9, 7.5))
    sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r",
                vmin=-1, vmax=1, square=True, linewidths=0.5,
                cbar_kws={"shrink": 0.7}, annot_kws={"size": 7}, ax=ax)
    ax.set_title("Spearman correlation (lower triangle)")
    return _save(fig, "04_correlation_heatmap.png")


def categorical_disease_rate(df):
    cols = config.CATEGORICAL_FEATURES + config.BINARY_FEATURES
    fig, axes = plt.subplots(2, 4, figsize=(14, 6.5))
    overall = df[config.TARGET].mean()
    for ax, col in zip(axes.ravel(), cols + ["ca"]):
        rate = df.groupby(col)[config.TARGET].agg(["mean", "size"])
        labels = [CODE_LABELS.get(col, {}).get(int(k), str(int(k)))
                  for k in rate.index]
        ax.bar(labels, rate["mean"], color="#5c946e")
        for i, (m, n) in enumerate(zip(rate["mean"], rate["size"])):
            ax.text(i, m + 0.02, f"n={n}", ha="center", fontsize=8)
        ax.axhline(overall, ls="--", color="grey", lw=1)
        ax.set_ylim(0, 1.1)
        ax.set_title(PRETTY[col])
        ax.tick_params(axis="x", labelrotation=25, labelsize=8)
    axes[0, 0].set_ylabel("Disease rate")
    axes[1, 0].set_ylabel("Disease rate")
    fig.suptitle("Disease rate per category (dashed = overall rate)", y=1.0)
    return _save(fig, "05_categorical_disease_rate.png")


def boxplots(df):
    long = df.melt(id_vars=config.TARGET,
                   value_vars=["age", "trestbps", "chol", "thalach"])
    long["Diagnosis"] = long[config.TARGET].map(CLASS_NAMES)
    g = sns.catplot(data=long, x="Diagnosis", y="value", col="variable",
                    kind="box", sharey=False, height=3.4, aspect=0.8,
                    palette=[CLASS_COLORS[0], CLASS_COLORS[1]],
                    hue="Diagnosis", legend=False)
    g.set_titles("{col_name}")
    g.set_xlabels("")
    g.figure.suptitle("Outlier check: continuous features by diagnosis",
                      y=1.03)
    return _save(g.figure, "06_boxplots.png")


def heart_rate_vs_age(df):
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for cls in (0, 1):
        sub = df[df[config.TARGET] == cls]
        ax.scatter(sub["age"], sub["thalach"], s=22, alpha=0.7,
                   color=CLASS_COLORS[cls], label=CLASS_NAMES[cls])
    ages = np.linspace(df["age"].min(), df["age"].max(), 50)
    ax.plot(ages, 220 - ages, color="black", lw=1.2,
            label="age-predicted max (220 - age)")
    ax.plot(ages, 0.85 * (220 - ages), color="black", lw=1, ls=":",
            label="85% of predicted max")
    ax.set_xlabel("Age")
    ax.set_ylabel("Max heart rate achieved (thalach)")
    ax.set_title("Motivation for the hr_reserve_ratio feature")
    ax.legend(fontsize=8)
    return _save(fig, "07_hr_vs_age.png")


def summary_table(df) -> pd.DataFrame:
    return df[config.CONTINUOUS_FEATURES].describe().T.round(2)


def run_all():
    raw = data.load_raw()
    df = data.load_clean()
    paths = [class_balance(df), missing_values(raw),
             continuous_histograms(df), correlation_heatmap(df),
             categorical_disease_rate(df), boxplots(df),
             heart_rate_vs_age(df)]
    summary_table(df).to_csv(OUT / "summary_stats.csv")
    return paths


if __name__ == "__main__":
    data.build_clean_dataset()
    for p in run_all():
        print(p)
