# Demo video script (target 5-7 minutes)

Record the screen (OBS / Xbox Game Bar `Win+Alt+R`) while walking through:

1. **Repo tour (30 s)** - README table, folder layout.
2. **Data + EDA (45 s)** - `python scripts/download_data.py`; open `notebooks/01_eda.ipynb`,
   show class balance, heatmap, the `hr_reserve_ratio` motivation plot.
3. **Training + MLflow (90 s)** - `python -m heart_risk.train --quick` (or show the
   full run log); `mlflow ui --backend-store-uri ./mlruns`; open the experiment,
   expand a parent run to show nested tuning runs, open champion run -> metrics,
   artifacts (plots, model).
4. **Tests + CI (60 s)** - `pytest -v`, `flake8`; GitHub Actions page with the
   lint -> test -> train -> docker jobs and their artifacts.
5. **Docker (45 s)** - `docker build`, `docker run`, `curl -X POST .../predict -d @sample_request.json`.
6. **Kubernetes (60 s)** - `bash scripts/deploy_k8s.sh`, `kubectl get pods,svc,ingress`,
   `minikube tunnel`, curl through the LoadBalancer IP.
7. **Monitoring (45 s)** - `python scripts/load_test.py -n 300 --url http://<IP>`;
   Grafana dashboard, Prometheus targets, `/monitor` page, `kubectl logs` JSON lines.
8. **Wrap-up (15 s)** - champion model metrics and next steps.
