"""Structured request logging and Prometheus metrics for the API."""

import json
import logging
import os
import statistics
import sys
import time
import uuid
from collections import Counter as Tally, deque
from datetime import datetime

from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

REQUESTS = Counter("heart_api_requests_total", "HTTP requests",
                   ["method", "endpoint", "status"])
LATENCY = Histogram("heart_api_request_latency_seconds",
                    "Request latency in seconds", ["endpoint"],
                    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2))
PREDICTIONS = Counter("heart_api_predictions_total",
                      "Predictions served by predicted label", ["label"])
RISK = Histogram("heart_api_risk_probability",
                 "Distribution of predicted P(heart disease)",
                 buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0))
ERRORS = Counter("heart_api_inference_errors_total",
                 "Failed inference calls")
MODEL_INFO = Gauge("heart_api_model_info", "Loaded model (value is 1)",
                   ["version", "family"])

# Paths that would only add noise to the request log.
_QUIET = {"/metrics", "/health", "/monitor", "/monitor/summary"}


class RecentActivity:
    """Rolling window of recent requests/predictions for the /monitor page."""

    def __init__(self, size: int = 500):
        self.started = time.time()
        self.requests = deque(maxlen=size)
        self.predictions = deque(maxlen=size)

    def add_request(self, path, status, latency_ms):
        self.requests.append({"ts": time.time(), "path": path,
                              "status": status, "latency_ms": latency_ms})

    def add_prediction(self, request_id, label, risk):
        self.predictions.append({"ts": time.time(), "request_id": request_id,
                                 "label": label, "risk": risk})

    def summary(self) -> dict:
        reqs = [r for r in self.requests if r["path"].startswith("/predict")]
        lat = sorted(r["latency_ms"] for r in reqs)
        statuses = Tally(str(r["status"]) for r in reqs)
        labels = Tally(p["label"] for p in self.predictions)
        risks = [p["risk"] for p in self.predictions]
        hist = [0] * 10
        for r in risks:
            hist[min(int(r * 10), 9)] += 1
        return {
            "uptime_s": round(time.time() - self.started),
            "window_requests": len(reqs),
            "status_counts": dict(statuses),
            "error_rate": round(sum(v for k, v in statuses.items()
                                    if k[0] in "45") / max(len(reqs), 1), 4),
            "latency_ms": {
                "p50": _pct(lat, 0.50), "p95": _pct(lat, 0.95),
                "max": lat[-1] if lat else None,
            },
            "label_counts": dict(labels),
            "mean_risk": round(statistics.fmean(risks), 4) if risks else None,
            "risk_histogram": hist,
            "recent": [
                {**p, "ts": datetime.fromtimestamp(p["ts"]).strftime(
                    "%H:%M:%S")} for p in list(self.predictions)[-12:][::-1]
            ],
        }


def _pct(sorted_vals, q):
    if not sorted_vals:
        return None
    return round(sorted_vals[min(int(q * len(sorted_vals)),
                                 len(sorted_vals) - 1)], 2)


ACTIVITY = RecentActivity()


class JsonFormatter(logging.Formatter):
    def format(self, record):
        entry = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        entry.update(getattr(record, "extra_fields", {}))
        return json.dumps(entry)


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("heart_api")
    if logger.handlers:
        return logger
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    handlers = [logging.StreamHandler(sys.stdout)]
    log_file = os.getenv("LOG_FILE")
    if log_file:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    for h in handlers:
        h.setFormatter(JsonFormatter())
        logger.addHandler(h)
    logger.propagate = False
    return logger


def log_event(logger, msg, **fields):
    logger.info(msg, extra={"extra_fields": fields})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attach a request id, time the request, log it and update metrics."""

    def __init__(self, app, logger):
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request, call_next):
        request_id = request.headers.get("x-request-id", uuid.uuid4().hex[:12])
        request.state.request_id = request_id
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["x-request-id"] = request_id
            return response
        finally:
            elapsed = time.perf_counter() - start
            route = request.scope.get("route")
            endpoint = getattr(route, "path", "unmatched")
            REQUESTS.labels(request.method, endpoint, str(status)).inc()
            LATENCY.labels(endpoint).observe(elapsed)
            if endpoint not in _QUIET:
                ACTIVITY.add_request(request.url.path, status,
                                     round(elapsed * 1000, 2))
                log_event(self.logger, "request", request_id=request_id,
                          method=request.method, path=request.url.path,
                          status=status,
                          latency_ms=round(elapsed * 1000, 2),
                          client=request.client.host if request.client
                          else None)
