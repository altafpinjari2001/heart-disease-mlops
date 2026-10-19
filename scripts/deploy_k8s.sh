#!/usr/bin/env bash
# Build the image, load it into Minikube and deploy API + monitoring.
#   bash scripts/deploy_k8s.sh
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE=heart-risk-api:1.0.0
NS=heart-risk

echo ">> building $IMAGE"
docker build -t "$IMAGE" .

echo ">> loading image into minikube"
minikube image load "$IMAGE"

echo ">> enabling ingress addon"
minikube addons enable ingress >/dev/null

echo ">> applying API manifests"
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-deployment.yaml -f k8s/02-service.yaml -f k8s/03-ingress.yaml
kubectl apply -f k8s/04-hpa.yaml || true

echo ">> monitoring config maps"
kubectl -n "$NS" create configmap prometheus-rules \
  --from-file=monitoring/alert_rules.yml --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$NS" create configmap grafana-datasources \
  --from-literal=datasource.yml="$(sed 's#http://prometheus:9090#http://prometheus.heart-risk.svc:9090#' monitoring/grafana/provisioning/datasources/datasource.yml)" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$NS" create configmap grafana-dashboard-provider \
  --from-file=monitoring/grafana/provisioning/dashboards/dashboards.yml \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$NS" create configmap grafana-dashboards \
  --from-file=monitoring/grafana/dashboards/heart-risk-api.json \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f k8s/monitoring/

echo ">> waiting for rollout"
kubectl -n "$NS" rollout status deployment/heart-risk-api --timeout=180s
kubectl -n "$NS" get pods,svc,ingress

cat <<EOF

Next steps:
  minikube tunnel                       # (separate terminal) gives the LoadBalancer an IP
  kubectl -n $NS get svc heart-risk-api # EXTERNAL-IP column
  curl -X POST http://<EXTERNAL-IP>/predict -H 'Content-Type: application/json' -d @sample_request.json
  minikube service -n $NS grafana --url
EOF
