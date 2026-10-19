"""Download the UCI Heart Disease (Cleveland) data and write the cleaned CSV.

    python scripts/download_data.py           # skip download if file exists
    python scripts/download_data.py --force   # re-download from UCI
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from heart_risk import data  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    df = data.build_clean_dataset(force_download=args.force)
    print(f"rows={len(df)} cols={df.shape[1]}")
    print("class balance:", df["target"].value_counts().to_dict())
    print("missing values:", data.missing_report(df).to_dict())


if __name__ == "__main__":
    main()
