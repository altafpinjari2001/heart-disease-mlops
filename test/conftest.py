import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from heart_risk import config  # noqa: E402


@pytest.fixture
def raw_frame():
    """Small raw-format frame mimicking the UCI file (incl. '?' -> NaN)."""
    rows = [
        [63, 1, 1, 145, 233, 1, 2, 150, 0, 2.3, 3, 0, 6, 0],
        [67, 1, 4, 160, 286, 0, 2, 108, 1, 1.5, 2, 3, 3, 2],
        [67, 1, 4, 120, 229, 0, 2, 129, 1, 2.6, 2, 2, 7, 1],
        [37, 1, 3, 130, 250, 0, 0, 187, 0, 3.5, 3, 0, 3, 0],
        [41, 0, 2, 130, 204, 0, 2, 172, 0, 1.4, 1, np.nan, 3, 0],
        [56, 1, 2, 120, 236, 0, 0, 178, 0, 0.8, 1, 0, np.nan, 4],
    ]
    return pd.DataFrame(rows, columns=config.RAW_COLUMNS)


@pytest.fixture
def synthetic_dataset():
    """Larger random but well-formed clean dataset for model tests."""
    rng = np.random.default_rng(0)
    n = 160
    df = pd.DataFrame({
        "age": rng.integers(30, 77, n),
        "sex": rng.integers(0, 2, n),
        "cp": rng.choice([1, 2, 3, 4], n),
        "trestbps": rng.integers(95, 190, n),
        "chol": rng.integers(150, 400, n),
        "fbs": rng.integers(0, 2, n),
        "restecg": rng.choice([0, 1, 2], n),
        "thalach": rng.integers(90, 200, n),
        "exang": rng.integers(0, 2, n),
        "oldpeak": rng.uniform(0, 5, n).round(1),
        "slope": rng.choice([1, 2, 3], n),
        "ca": rng.choice([0, 1, 2, 3], n).astype(float),
        "thal": rng.choice([3, 6, 7], n).astype(float),
    })
    signal = (df["cp"] == 4).astype(int) + df["exang"] + (df["ca"] > 0)
    df[config.TARGET] = (signal + rng.normal(0, 0.6, n) > 1.2).astype(int)
    df.loc[::17, "ca"] = np.nan
    return df
