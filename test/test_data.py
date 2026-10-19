import numpy as np

from heart_risk import config, data


def test_clean_creates_binary_target(raw_frame):
    out = data.clean(raw_frame)
    assert "num" not in out.columns
    assert set(out[config.TARGET].unique()) <= {0, 1}
    # num 2, 1 and 4 all map to disease present
    assert out[config.TARGET].tolist() == [0, 1, 1, 0, 0, 1]


def test_clean_keeps_missing_for_pipeline_imputation(raw_frame):
    out = data.clean(raw_frame)
    assert out["ca"].isna().sum() == 1
    assert out["thal"].isna().sum() == 1
    assert data.missing_report(out).to_dict() == {"ca": 1, "thal": 1}


def test_clean_flags_out_of_range_values(raw_frame):
    raw_frame.loc[0, "chol"] = 0          # physiologically impossible
    raw_frame.loc[1, "thal"] = 5          # not a valid UCI code
    out = data.clean(raw_frame)
    assert np.isnan(out.loc[0, "chol"])
    assert np.isnan(out.loc[1, "thal"])


def test_clean_drops_duplicates(raw_frame):
    doubled = raw_frame.loc[[0, 0, 1]]
    assert len(data.clean(doubled)) == 2


def test_load_raw_parses_question_marks(tmp_path):
    f = tmp_path / "raw.data"
    f.write_text("63.0,1.0,1.0,145.0,233.0,1.0,2.0,150.0,0.0,2.3,3.0,?,6.0,0\n")
    df = data.load_raw(f)
    assert list(df.columns) == config.RAW_COLUMNS
    assert np.isnan(df.loc[0, "ca"])


def test_split_xy_columns(raw_frame):
    X, y = data.split_xy(data.clean(raw_frame))
    assert list(X.columns) == config.FEATURES
    assert len(X) == len(y)


def test_download_skips_when_present(tmp_path, monkeypatch):
    f = tmp_path / "raw.data"
    f.write_text("x")

    def boom(*a, **k):
        raise AssertionError("network should not be called")

    monkeypatch.setattr(data.requests, "get", boom)
    assert data.download_raw(dest=f) == f
