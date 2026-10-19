"""Inference helpers used by the API, the notebook and the CLI."""

import argparse
import json
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from heart_risk import config

LABELS = {0: "no_heart_disease", 1: "heart_disease"}


@lru_cache(maxsize=2)
def load_model(path: str = str(config.MODEL_PATH)):
    return joblib.load(path)


def load_metadata(path: Path = config.MODEL_METADATA_PATH) -> dict:
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else {}


def predict_records(records, model=None, threshold: float = 0.5) -> list:
    """Predict for a list of dicts with the 13 raw UCI feature columns."""
    model = model or load_model()
    frame = pd.DataFrame(records).reindex(columns=config.FEATURES)
    frame = frame.apply(pd.to_numeric, errors="coerce")
    probs = model.predict_proba(frame)[:, 1]
    out = []
    for p in probs:
        pred = int(p >= threshold)
        out.append({
            "prediction": pred,
            "label": LABELS[pred],
            "confidence": round(float(p if pred else 1 - p), 4),
            "risk_probability": round(float(p), 4),
        })
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Score patients from JSON")
    parser.add_argument("json_file", help="file with one record or a list")
    args = parser.parse_args(argv)
    payload = json.loads(Path(args.json_file).read_text())
    records = payload if isinstance(payload, list) else [payload]
    print(json.dumps(predict_records(records), indent=2))


if __name__ == "__main__":
    main()
