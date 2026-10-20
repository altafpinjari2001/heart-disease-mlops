# Heart Disease Risk — End-to-End MLOps Pipeline

[![ci-cd](https://github.com/altafpinjari2001/heart-disease-mlops/actions/workflows/ci.yml/badge.svg)](https://github.com/altafpinjari2001/heart-disease-mlops/actions/workflows/ci.yml)

MLOps (AIMLCZG523) Assignment 01 - Altaf Anwar Pinjari (2025AE05638). A classifier that predicts the presence of heart
disease from 13 clinical attributes (UCI Heart Disease, Cleveland), served as a
monitored, containerised FastAPI service on Kubernetes.

| Item | Where |
|---|---|
| Data download + cleaning | `scripts/download_data.py`, `heart_risk/data.py` |
| EDA | `notebooks/01_eda.ipynb`, `heart_risk/eda.py` → `reports/figures/eda/` |
| Features + models | `heart_risk/features.py`, `heart_risk/train.py`, `notebooks/02_model_training.ipynb` |
| Experiment tracking | MLflow, file store in `mlruns/` (68 runs) |
| Packaged model | `models/heart_model.joblib`, `models/mlflow_model/`, `models/model_metadata.json` |
| Inference | `heart_risk/predict.py`, `notebooks/03_inference.ipynb` |
| API | `api/` (FastAPI: `/predict`, `/predict/batch`, `/health`, `/model-info`, `/metrics`, `/monitor`) |
| Unit tests | `test/` (28 pytest tests) |
| CI/CD | `.github/workflows/ci.yml` |
| Container | `Dockerfile`, `docker-compose.yml` |
| Kubernetes | `k8s/` (Deployment, LoadBalancer Service, Ingress, HPA, Prometheus, Grafana) |
| Monitoring | `monitoring/` (Prometheus config + alert rules, Grafana dashboard) |
| Screenshots | `screenshots/` |
| Report | `reports/MLOps_Assignment1_Report.docx` |

## 1. Setup (clean environment)

Python 3.11 is used everywhere (local, CI and container).

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt   # = requirements.txt + pytest/flake8/httpx
```

## 2. Run the pipeline

```bash
python scripts/download_data.py          # UCI download -> data/raw, cleaned CSV -> data/processed
python -m heart_risk.eda                 # EDA figures -> reports/figures/eda
python -m heart_risk.train               # grid search x3 models, MLflow logging, champion -> models/
python scripts/experiment_summary.py     # summary of all MLflow runs
mlflow ui --backend-store-uri ./mlruns   # browse runs at http://127.0.0.1:5000
pytest -v                                # unit tests
flake8                                   # lint
```

`python -m heart_risk.train --quick` runs tiny grids (handy for smoke tests).

Manual download alternative: get `processed.cleveland.data` from
<https://archive.ics.uci.edu/dataset/45/heart+disease> and place it in `data/raw/`.

## 3. Serve the model

**Locally**

```bash
uvicorn api.main:app --port 8000
curl -X POST http://127.0.0.1:8000/predict -H "Content-Type: application/json" -d @sample_request.json
# {"prediction":1,"label":"heart_disease","confidence":0.9767,"risk_probability":0.9767,"model_version":"1.0.0","request_id":"..."}
```

Swagger UI: <http://127.0.0.1:8000/docs> · live monitor: <http://127.0.0.1:8000/monitor> ·
Prometheus metrics: <http://127.0.0.1:8000/metrics>

**Docker**

```bash
docker build -t heart-risk-api:1.0.0 .
docker run -d --name heart-api -p 8000:8000 heart-risk-api:1.0.0
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d @sample_request.json
docker logs heart-api
```

**Docker Compose (API + Prometheus + Grafana)**

```bash
docker compose up -d --build
python scripts/load_test.py -n 300       # generate traffic
# API :8000   Prometheus :9090   Grafana :3000 (admin/admin, dashboard "Heart Risk API - Monitoring")
```

## 4. Deploy to Kubernetes (Docker Desktop or Minikube)

Tested on Docker Desktop 29.9 with its built-in Kubernetes (v1.36.1):

```bash
bash scripts/deploy_k8s.sh               # Windows: powershell -ExecutionPolicy Bypass -File scripts\deploy_k8s.ps1
kubectl -n heart-risk get pods,svc,ingress,hpa
```

The script builds the image, installs the NGINX ingress controller and
metrics-server, applies the API Deployment (2 replicas, probes, limits),
LoadBalancer Service, Ingress, HPA (2-5 replicas) and Prometheus + Grafana.

**Access instructions (local cluster, no public URL):**

| What | How |
|---|---|
| API via LoadBalancer | `curl -X POST http://localhost:8080/predict -H "Content-Type: application/json" -d @sample_request.json` |
| API via Ingress | `kubectl -n ingress-nginx port-forward svc/ingress-nginx-controller 8088:80` then `curl -H "Host: heart-risk.local" http://localhost:8088/health` |
| Prometheus | `kubectl -n heart-risk port-forward svc/prometheus 9090:9090` → <http://localhost:9090/targets> |
| Grafana | `kubectl -n heart-risk port-forward svc/grafana 3000:3000` → <http://localhost:3000> (admin / admin, anonymous read-only enabled) |
| Generate traffic | `python scripts/load_test.py --url http://127.0.0.1:8080 -n 500` |

Docker Desktop's load balancer serves a single LoadBalancer service, so the API
gets it (port 8080) and the ingress controller runs as NodePort and is reached
with a port-forward. On **Minikube** (`minikube start`, then the same script)
run `minikube tunnel` and use the EXTERNAL-IP of `svc/heart-risk-api`, or add
`<minikube ip> heart-risk.local` to your hosts file for the Ingress.

## 5. CI/CD

`.github/workflows/ci.yml` runs on every push/PR to `main`:

1. **lint** – flake8 (report uploaded as artifact)
2. **test** – pytest with JUnit + coverage reports (artifact)
3. **train** – download data, train all models with MLflow, quality gate
   (test ROC-AUC ≥ 0.85), upload model + figures + `mlruns` (artifacts)
4. **docker** – build image, run container, smoke-test `/predict`, upload response,
   container logs and the image tarball

Each job depends on the previous one, so any lint, test, training or container
failure stops the pipeline with the failing step's log.

## 6. Results (held-out test split, 61 patients)

| Model | CV ROC-AUC | Test accuracy | Test precision | Test recall | Test ROC-AUC |
|---|---|---|---|---|---|
| **Logistic regression (champion)** | **0.907** | 0.869 | 0.813 | 0.929 | 0.961 |
| Random forest | 0.900 | 0.885 | 0.839 | 0.929 | 0.959 |
| Gradient boosting | 0.886 | 0.902 | 0.867 | 0.929 | 0.961 |

The champion is chosen on cross-validated ROC-AUC (training split only); the
test split is used only for reporting.

## Repository

GitHub: <https://github.com/altafpinjari2001/heart-disease-mlops>
