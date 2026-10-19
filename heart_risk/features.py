"""Feature engineering + preprocessing pipeline shared by training and serving."""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from heart_risk import config

ENGINEERED_FEATURES = ["hr_reserve_ratio"]


class ClinicalFeatureBuilder(BaseEstimator, TransformerMixin):
    """Adds domain-driven features before column-wise preprocessing.

    hr_reserve_ratio = thalach / (220 - age): the share of the age-predicted
    maximum heart rate reached during the exercise test. A low ratio
    (chronotropic incompetence) is a known cardiac risk marker and is more
    informative than raw thalach, which naturally falls with age.
    """

    def fit(self, X, y=None):
        self.feature_names_in_ = np.asarray(list(X.columns), dtype=object)
        return self

    def transform(self, X):
        X = pd.DataFrame(X, columns=self.feature_names_in_).copy()
        predicted_max = 220.0 - X["age"]
        X["hr_reserve_ratio"] = X["thalach"] / predicted_max.where(
            predicted_max > 0)
        return X

    def get_feature_names_out(self, input_features=None):
        return np.asarray(list(self.feature_names_in_) + ENGINEERED_FEATURES,
                          dtype=object)


def build_preprocessor() -> Pipeline:
    numeric = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
    ])
    binary = Pipeline([
        ("impute", SimpleImputer(strategy="most_frequent")),
    ])
    categorical = Pipeline([
        ("impute", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(
            categories=[config.CATEGORY_LEVELS[c]
                        for c in config.CATEGORICAL_FEATURES],
            handle_unknown="ignore",
            sparse_output=False,
        )),
    ])
    columns = ColumnTransformer([
        ("num", numeric, config.CONTINUOUS_FEATURES + ENGINEERED_FEATURES),
        ("bin", binary, config.BINARY_FEATURES),
        ("cat", categorical, config.CATEGORICAL_FEATURES),
    ])
    return Pipeline([
        ("clinical", ClinicalFeatureBuilder()),
        ("columns", columns),
    ])


def build_pipeline(estimator) -> Pipeline:
    """Full model pipeline: raw patient columns in, class probability out."""
    return Pipeline([
        ("preprocess", build_preprocessor()),
        ("model", estimator),
    ])


def transformed_feature_names(pipeline: Pipeline) -> list:
    cols = pipeline.named_steps["preprocess"].named_steps["columns"]
    names = [n.split("__", 1)[1] for n in cols.get_feature_names_out()]
    # one-hot names come out as "cp_4.0" because imputation yields floats
    return [n[:-2] if n.endswith(".0") else n for n in names]
