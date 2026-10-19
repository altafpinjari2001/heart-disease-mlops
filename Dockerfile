# ---------- build stage: compile wheels once ----------
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements-api.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements-api.txt

# ---------- runtime stage ----------
FROM python:3.11-slim
LABEL org.opencontainers.image.title="heart-disease-risk-api" \
      org.opencontainers.image.description="FastAPI service for UCI heart disease risk prediction"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_PATH=/app/models/heart_model.joblib \
    LOG_FILE=/app/logs/api.log \
    PORT=8000

WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels \
 && useradd --create-home --uid 1001 appuser \
 && mkdir -p /app/logs && chown appuser /app/logs

COPY heart_risk/ heart_risk/
COPY api/ api/
COPY models/heart_model.joblib models/model_metadata.json models/

USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
