"""Draw the system architecture diagram -> reports/figures/architecture.png"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from heart_risk import config  # noqa: E402

LANES = [  # (title, y, colour)
    ("1  Data & experimentation", 7.6, "#e7f1f5"),
    ("2  CI/CD (GitHub Actions)", 5.2, "#fdf1e3"),
    ("3  Serving & deployment (Kubernetes)", 2.8, "#e9f4ec"),
    ("4  Monitoring", 0.4, "#f8e8ea"),
]

BOXES = {
    # key: (x, y, w, h, label)
    "uci": (0.3, 7.9, 2.0, 1.1, "UCI repository\nprocessed.cleveland"),
    "dl": (2.8, 7.9, 2.2, 1.1, "download_data.py\nclean -> heart_clean.csv"),
    "eda": (5.5, 8.55, 2.0, 0.75, "EDA notebook\n7 figures"),
    "train": (5.5, 7.75, 2.0, 0.75, "heart_risk.train\nGridSearchCV x3"),
    "mlflow": (8.0, 7.9, 2.2, 1.1, "MLflow tracking\n68 runs, params,\nmetrics, plots"),
    "model": (10.7, 7.9, 2.3, 1.1, "Champion pipeline\nheart_model.joblib\n+ MLflow model"),
    "push": (0.3, 5.5, 2.0, 1.1, "git push / PR\nto main"),
    "lint": (2.8, 5.5, 1.6, 1.1, "flake8\nlint"),
    "test": (4.8, 5.5, 1.7, 1.1, "pytest\n28 tests\n+ coverage"),
    "ci_train": (6.9, 5.5, 1.9, 1.1, "train + quality\ngate AUC>=0.85"),
    "build": (9.2, 5.5, 1.9, 1.1, "docker build\n+ smoke test"),
    "art": (11.5, 5.5, 1.5, 1.1, "artifacts:\nmodel, logs,\nimage.tar"),
    "client": (0.3, 3.1, 2.0, 1.1, "Client\ncurl / Swagger /\nload_test.py"),
    "ing": (2.8, 3.1, 2.0, 1.1, "Ingress (nginx)\nLoadBalancer svc"),
    "pods": (5.3, 3.1, 3.2, 1.1, "Deployment: 2-5 replicas (HPA)\nFastAPI + uvicorn\n/predict /health /metrics"),
    "img": (9.6, 3.1, 2.6, 1.1, "Docker image\nheart-risk-api:1.0.0"),
    "logs": (0.5, 0.7, 2.2, 1.1, "Structured JSON logs\nstdout + /app/logs"),
    "prom": (3.3, 0.7, 2.4, 1.1, "Prometheus\npod discovery,\nalert rules"),
    "graf": (6.4, 0.7, 2.4, 1.1, "Grafana dashboard\nrate, latency,\nrisk distribution"),
    "mon": (9.5, 0.7, 2.4, 1.1, "/monitor page\nbuilt-in live\nAPI dashboard"),
}

ARROWS = [
    ("uci", "dl"), ("dl", "eda"), ("dl", "train"), ("train", "mlflow"),
    ("mlflow", "model"),
    ("push", "lint"), ("lint", "test"), ("test", "ci_train"),
    ("ci_train", "build"), ("build", "art"),
    ("client", "ing"), ("ing", "pods"), ("img", "pods"), ("pods", "logs"),
    ("pods", "prom"), ("prom", "graf"), ("pods", "mon"),
    ("model", "build"), ("build", "img"),
]


def anchor(box, other):
    x, y, w, h, _ = BOXES[box]
    ox, oy, ow, oh, _ = BOXES[other]
    cx, cy, ocx, ocy = x + w / 2, y + h / 2, ox + ow / 2, oy + oh / 2
    if abs(cy - ocy) < 1.0:  # same lane -> horizontal
        return (x + w, cy) if ocx > cx else (x, cy)
    return (cx, y) if ocy < cy else (cx, y + h)


def main():
    fig, ax = plt.subplots(figsize=(13.5, 9.6))
    ax.set_xlim(0, 13.3)
    ax.set_ylim(0.2, 9.9)
    ax.axis("off")
    for title, y, color in LANES:
        ax.add_patch(FancyBboxPatch((0.1, y), 13.1, 2.0,
                                    boxstyle="round,pad=0.02,rounding_size=0.1",
                                    fc=color, ec="none"))
        ax.text(0.2, y + 1.82, title, fontsize=10.5, weight="bold",
                color="#33424d")
    for key, (x, y, w, h, label) in BOXES.items():
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                                    boxstyle="round,pad=0.02,rounding_size=0.08",
                                    fc="white", ec="#5a6b78", lw=1.1))
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
                fontsize=8.2)
    for a, b in ARROWS:
        ax.add_patch(FancyArrowPatch(anchor(a, b), anchor(b, a),
                                     arrowstyle="-|>", mutation_scale=11,
                                     color="#1f6f8b", lw=1.2,
                                     connectionstyle="arc3,rad=0.0"))
    ax.set_title("Heart disease risk - MLOps architecture", fontsize=14,
                 weight="bold")
    out = config.FIGURES_DIR / "architecture.png"
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    print(out)


if __name__ == "__main__":
    main()
