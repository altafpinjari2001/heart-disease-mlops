"""Data acquisition and cleaning for the UCI Cleveland heart disease dataset."""

from pathlib import Path
import logging

import numpy as np
import pandas as pd
import requests

from heart_risk import config

log = logging.getLogger(__name__)

# Plausible physiological ranges; anything outside is treated as missing.
VALID_RANGES = {
    "age": (18, 100),
    "trestbps": (70, 250),
    "chol": (100, 650),
    "thalach": (60, 230),
    "oldpeak": (0, 7),
    "ca": (0, 3),
}


def download_raw(url: str = config.UCI_URL,
                 dest: Path = config.RAW_DATA_PATH,
                 force: bool = False) -> Path:
    """Download the raw Cleveland file from UCI (skipped if already present)."""
    dest = Path(dest)
    if dest.exists() and not force:
        log.info("Raw data already present at %s", dest)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    log.info("Downloading %s", url)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    log.info("Saved %d bytes to %s", len(resp.content), dest)
    return dest


def load_raw(path: Path = config.RAW_DATA_PATH) -> pd.DataFrame:
    """Read the header-less raw file; '?' marks missing values in the source."""
    return pd.read_csv(path, header=None, names=config.RAW_COLUMNS,
                       na_values="?")


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Return a typed, de-duplicated frame with a binary ``target`` column.

    Missing values are *kept* as NaN on purpose: they are imputed inside the
    sklearn pipeline so the exact same logic is applied at training and
    inference time (no train/serve skew, no leakage from the test split).
    """
    out = df.copy()
    out = out.apply(pd.to_numeric, errors="coerce")

    # num: 0 = no disease, 1-4 = increasing severity -> binary presence.
    out[config.TARGET] = (out["num"] > 0).astype(int)
    out = out.drop(columns=["num"])

    for col, (lo, hi) in VALID_RANGES.items():
        bad = ~out[col].between(lo, hi) & out[col].notna()
        if bad.any():
            log.warning("%s: %d out-of-range values set to NaN", col, bad.sum())
            out.loc[bad, col] = np.nan

    for col, levels in config.CATEGORY_LEVELS.items():
        bad = ~out[col].isin(levels) & out[col].notna()
        out.loc[bad, col] = np.nan

    before = len(out)
    out = out.drop_duplicates().reset_index(drop=True)
    if len(out) != before:
        log.info("Dropped %d duplicate rows", before - len(out))

    int_cols = config.BINARY_FEATURES + [config.TARGET]
    out[int_cols] = out[int_cols].astype("int64")
    return out


def missing_report(df: pd.DataFrame) -> pd.Series:
    """Count of missing values per column (only columns that have any)."""
    counts = df.isna().sum()
    return counts[counts > 0]


def load_clean(path: Path = config.CLEAN_DATA_PATH) -> pd.DataFrame:
    return pd.read_csv(path)


def build_clean_dataset(force_download: bool = False) -> pd.DataFrame:
    """Download (if needed), clean and persist the dataset; returns it."""
    download_raw(force=force_download)
    df = clean(load_raw())
    config.CLEAN_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.CLEAN_DATA_PATH, index=False)
    log.info("Clean dataset: %d rows x %d cols -> %s",
             *df.shape, config.CLEAN_DATA_PATH)
    return df


def split_xy(df: pd.DataFrame):
    return df[config.FEATURES], df[config.TARGET]
