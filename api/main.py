"""FastAPI service exposing the heart disease risk model.

    uvicorn api.main:app --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from api import dashboard
from api import monitoring as mon
from api.schemas import (BatchRequest, BatchResponse, PatientFeatures,
                         PredictionResponse)
from heart_risk import config
from heart_risk.predict import load_metadata, load_model, predict_records

logger = mon.setup_logging()
STATE = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    STATE["model"] = load_model(str(config.MODEL_PATH))
    STATE["meta"] = load_metadata()
    meta = STATE["meta"]
    mon.MODEL_INFO.labels(meta.get("model_version", "unknown"),
                          meta.get("family", "unknown")).set(1)
    mon.log_event(logger, "model_loaded", path=str(config.MODEL_PATH),
                  family=meta.get("family"),
                  version=meta.get("model_version"))
    yield
    STATE.clear()


app = FastAPI(title="Heart Disease Risk API", version="1.0.0",
              description="Predicts presence of heart disease from 13 UCI "
                          "clinical attributes.", lifespan=lifespan)
app.add_middleware(mon.RequestLoggingMiddleware, logger=logger)


def _score(patients, request_id):
    threshold = STATE["meta"].get("decision_threshold", 0.5)
    try:
        results = predict_records([p.model_dump() for p in patients],
                                  model=STATE["model"], threshold=threshold)
    except Exception as exc:  # pragma: no cover - defensive
        mon.ERRORS.inc()
        logger.exception("inference failed")
        raise HTTPException(status_code=500, detail="inference failed") \
            from exc
    version = STATE["meta"].get("model_version", "unknown")
    for patient, res in zip(patients, results):
        mon.PREDICTIONS.labels(res["label"]).inc()
        mon.RISK.observe(res["risk_probability"])
        mon.ACTIVITY.add_prediction(request_id, res["label"],
                                    res["risk_probability"])
        mon.log_event(logger, "prediction", request_id=request_id,
                      inputs=patient.model_dump(), **res)
    return [PredictionResponse(**r, model_version=version,
                               request_id=request_id) for r in results]


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": "model" in STATE}


@app.get("/model-info")
def model_info():
    return STATE.get("meta", {})


@app.post("/predict", response_model=PredictionResponse)
def predict(patient: PatientFeatures, request: Request):
    return _score([patient], request.state.request_id)[0]


@app.post("/predict/batch", response_model=BatchResponse)
def predict_batch(batch: BatchRequest, request: Request):
    return {"predictions": _score(batch.patients, request.state.request_id)}


@app.get("/monitor/summary")
def monitor_summary():
    return mon.ACTIVITY.summary()


@app.get("/monitor", response_class=HTMLResponse, include_in_schema=False)
def monitor_page(refresh: int = 5):
    return dashboard.render(mon.ACTIVITY.summary(), STATE.get("meta", {}),
                            refresh=max(refresh, 0))


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
