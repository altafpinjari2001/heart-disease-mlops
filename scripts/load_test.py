"""Send a stream of realistic requests to the API to populate the dashboards.

    python scripts/load_test.py --url http://localhost:8000 -n 300
"""

import argparse
import random
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from heart_risk import config  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("-n", type=int, default=200)
    ap.add_argument("--invalid-share", type=float, default=0.05,
                    help="fraction of deliberately invalid payloads")
    ap.add_argument("--sleep", type=float, default=0.05)
    args = ap.parse_args()

    df = pd.read_csv(config.CLEAN_DATA_PATH)[config.FEATURES]
    codes = {}
    for _ in range(args.n):
        rec = df.sample(1).iloc[0].dropna().to_dict()
        rec = {k: (int(v) if k not in ("oldpeak",) else float(v))
               for k, v in rec.items()}
        if random.random() < args.invalid_share:
            rec["age"] = 150  # triggers a 422 validation error
        r = requests.post(f"{args.url}/predict", json=rec, timeout=10)
        codes[r.status_code] = codes.get(r.status_code, 0) + 1
        time.sleep(args.sleep)
    print("status codes:", codes)


if __name__ == "__main__":
    main()
