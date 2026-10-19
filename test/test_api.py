"""API tests run against a small model trained on synthetic data, so they
do not depend on the committed artefact or on network access."""

import json

import joblib
import pytest
from fastapi.testclient import TestClient
from sklearn.linear_model import LogisticRegression

from api.schemas import EXAMPLE_PATIENT
from heart_risk import config
from heart_risk.features import build_pipeline


@pytest.fixture
def client(synthetic_dataset, tmp_path, monkeypatch):
    pipe = build_pipeline(LogisticRegression(max_iter=1000)).fit(
        synthetic_dataset[config.FEATURES], synthetic_dataset[config.TARGET])
    model_path = tmp_path / "model.joblib"
    joblib.dump(pipe, model_path)
    meta_path = tmp_path / "meta.json"
    meta_path.write_text(json.dumps({"model_version": "test",
                                     "family": "logistic_regression",
                                     "decision_threshold": 0.5}))
    monkeypatch.setattr(config, "MODEL_PATH", model_path)
    monkeypatch.setattr(config, "MODEL_METADATA_PATH", meta_path)
    import api.main as main
    monkeypatch.setattr(main, "load_metadata",
                        lambda: json.loads(meta_path.read_text()))
    with TestClient(main.app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "model_loaded": True}


def test_predict_returns_prediction_and_confidence(client):
    r = client.post("/predict", json=EXAMPLE_PATIENT)
    assert r.status_code == 200
    body = r.json()
    assert body["prediction"] in (0, 1)
    assert 0.5 <= body["confidence"] <= 1
    assert body["model_version"] == "test"
    assert r.headers["x-request-id"] == body["request_id"]


def test_predict_without_optional_fields(client):
    patient = {k: v for k, v in EXAMPLE_PATIENT.items()
               if k not in ("ca", "thal")}
    assert client.post("/predict", json=patient).status_code == 200


@pytest.mark.parametrize("field,value", [("age", 5), ("cp", 9),
                                         ("chol", "high")])
def test_predict_rejects_invalid_input(client, field, value):
    bad = {**EXAMPLE_PATIENT, field: value}
    assert client.post("/predict", json=bad).status_code == 422


def test_predict_rejects_unknown_field(client):
    assert client.post("/predict",
                       json={**EXAMPLE_PATIENT, "foo": 1}).status_code == 422


def test_batch(client):
    r = client.post("/predict/batch",
                    json={"patients": [EXAMPLE_PATIENT, EXAMPLE_PATIENT]})
    assert r.status_code == 200
    assert len(r.json()["predictions"]) == 2


def test_metrics_exposed(client):
    client.post("/predict", json=EXAMPLE_PATIENT)
    text = client.get("/metrics").text
    assert "heart_api_requests_total" in text
    assert "heart_api_predictions_total" in text
    assert "heart_api_risk_probability_bucket" in text


def test_monitor_dashboard(client):
    client.post("/predict", json=EXAMPLE_PATIENT)
    summary = client.get("/monitor/summary").json()
    assert summary["window_requests"] >= 1
    assert sum(summary["risk_histogram"]) >= 1
    page = client.get("/monitor")
    assert page.status_code == 200
    assert "live monitor" in page.text


def test_model_info(client):
    assert client.get("/model-info").json()["family"] == "logistic_regression"
