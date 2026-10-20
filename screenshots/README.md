# Screenshots

All screenshots were captured from the running pipeline (local machine with
Docker Desktop 29.9 + Kubernetes v1.36.1, and GitHub Actions).

| File | Shows |
|---|---|
| `01_data_download.png` | `scripts/download_data.py` downloading + cleaning the UCI data |
| `03_mlflow_experiment_runs.png` | MLflow experiment `heart-disease-risk` with the 3 model families + champion run |
| `04_mlflow_lr_run_details.png` | Champion run: parameters, CV + test metrics, tags, logged model |
| `05_mlflow_artifacts_roc.png` | Logged artifacts (plots/, cv/, model/) - ROC curve |
| `06_local_tests_lint_coverage.png` | flake8 (0 issues) + 28 pytest tests passing with coverage |
| `07_github_actions_pipeline.png` | GitHub Actions run #1 - lint, test, train, docker jobs all green |
| `07b_github_actions_docker_job.png` | CI docker job log: build, run, /health + /predict smoke test |
| `08_api_swagger_docs.png` | FastAPI Swagger UI |
| `09_api_predict_curl.png` | curl: `/health`, `/predict` (both classes), 422 on invalid input, `/model-info` |
| `10_api_swagger_predict.png` | `/predict` request schema / example |
| `11_api_monitor_dashboard.png` | Built-in `/monitor` dashboard after 300 requests |
| `12_api_json_logs.png` | Structured JSON request + prediction logs |
| `13_prometheus_metrics_endpoint.png` | `/metrics` Prometheus exposition |
| `14_docker_build.png` | Local `docker build -t heart-risk-api:1.0.0 .` |
| `15_docker_run_predict.png` | `docker run`, `docker ps`, `/health` + `/predict` from the container, `docker logs` |
| `16_k8s_resources.png` | `kubectl get deploy,pods,svc,ingress,hpa` - HPA scaled 2 -> 4 under load |
| `17_k8s_predict_loadbalancer.png` | Predictions via the LoadBalancer (`localhost:8080`) and the NGINX Ingress |
| `18_grafana_dashboard.png` | Grafana "Heart Risk API - Monitoring" (in-cluster) after the load test |
| `19_prometheus_targets.png` | Prometheus pod discovery - 4/4 API replicas UP |
