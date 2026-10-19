import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from heart_risk import config
from heart_risk.features import (ClinicalFeatureBuilder, build_pipeline,
                                 build_preprocessor,
                                 transformed_feature_names)


def test_hr_reserve_ratio_value():
    X = pd.DataFrame({"age": [40.0], "thalach": [162.0]})
    out = ClinicalFeatureBuilder().fit(X).transform(X)
    assert np.isclose(out.loc[0, "hr_reserve_ratio"], 162 / 180)


def test_preprocessor_output_has_no_nans(synthetic_dataset):
    X = synthetic_dataset[config.FEATURES]
    assert X.isna().any().any()
    Xt = build_preprocessor().fit_transform(X)
    assert not np.isnan(Xt).any()


def test_preprocessor_shape_is_stable(synthetic_dataset):
    X = synthetic_dataset[config.FEATURES]
    pre = build_preprocessor().fit(X)
    # 7 scaled numeric + 3 binary + one-hot(4 + 3 + 3 + 3)
    assert pre.transform(X).shape[1] == 7 + 3 + 13
    # A single row with unseen/missing categories must still transform
    row = X.head(1).copy()
    row["thal"] = np.nan
    assert pre.transform(row).shape == (1, 23)


def test_scaled_features_are_standardised(synthetic_dataset):
    X = synthetic_dataset[config.FEATURES].dropna()
    Xt = build_preprocessor().fit_transform(X)
    assert np.allclose(Xt[:, :7].mean(axis=0), 0, atol=1e-7)


def test_feature_names(synthetic_dataset):
    pipe = build_pipeline(LogisticRegression(max_iter=500))
    pipe.fit(synthetic_dataset[config.FEATURES],
             synthetic_dataset[config.TARGET])
    names = transformed_feature_names(pipe)
    assert "hr_reserve_ratio" in names
    assert "cp_4" in names
    assert len(names) == 23
