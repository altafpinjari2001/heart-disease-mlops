# Screenshots

## Already captured (taken from the running pipeline)

| File | Shows |
|---|---|
| `01_data_download.png` | `scripts/download_data.py` downloading + cleaning the UCI data |
| `03_mlflow_experiment_runs.png` | MLflow experiment `heart-disease-risk` with the 3 model families + champion run |
| `04_mlflow_lr_run_details.png` | Champion run: parameters, CV + test metrics, tags, logged model |
| `05_mlflow_artifacts_roc.png` | Logged artifacts (plots/, cv/, model/) - ROC curve |
| `06_local_tests_lint_coverage.png` | flake8 (0 issues) + 28 pytest tests passing with coverage |
| `08_api_swagger_docs.png` | FastAPI Swagger UI |
| `10_api_swagger_predict.png` | `/predict` request schema / example |
| `09_api_predict_curl.png` | curl calls: `/health`, `/predict` (both classes), 422 on invalid input, `/model-info` |
| `11_api_monitor_dashboard.png` | Built-in `/monitor` dashboard after 300 requests |
| `12_api_json_logs.png` | Structured JSON request + prediction logs |
| `13_prometheus_metrics_endpoint.png` | `/metrics` Prometheus exposition |

## To capture after running on a machine with Docker / Minikube / GitHub

Docker and Kubernetes were not available on the machine used to build this
project, so these must be captured by running the commands in the main README.
Save them with these names (the report references them):

| File | Command / page |
|---|---|
| `07_github_actions_pipeline.png` | GitHub -> Actions -> `ci-cd` run with the 4 green jobs + artifacts list |
| `14_docker_build.png` | `docker build -t heart-risk-api:1.0.0 .` finishing successfully |
| `15_docker_run_predict.png` | `docker run -d -p 8000:8000 ...` + `curl .../predict` + `docker ps` |
| `16_k8s_resources.png` | `kubectl -n heart-risk get pods,svc,ingress,hpa` |
| `17_k8s_predict_loadbalancer.png` | `curl http://<EXTERNAL-IP>/predict ...` through the LoadBalancer / Ingress |
| `18_grafana_dashboard.png` | Grafana "Heart Risk API - Monitoring" after `scripts/load_test.py` |
| `19_prometheus_targets.png` | Prometheus -> Status -> Targets showing API pods UP |
