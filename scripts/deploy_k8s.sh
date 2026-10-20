#!/usr/bin/env bash
# Build the image and deploy API + Ingress + HPA + monitoring to a local
# cluster. Works with Docker Desktop Kubernetes (default) and Minikube.
#   bash scripts/deploy_k8s.sh
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE=heart-risk-api:1.0.0
NS=heart-risk
INGRESS_NGINX=https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.12.1/deploy/static/provider/cloud/deploy.yaml
METRICS_SERVER=https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.7.2/components.yaml
CTX=$(kubectl config current-context)
echo ">> kube context: $CTX"

echo ">> building $IMAGE"
docker build -t "$IMAGE" .

if [[ "$CTX" == minikube ]]; then
  minikube image load "$IMAGE"
  minikube addons enable ingress >/dev/null
  minikube addons enable metrics-server >/dev/null
else
  # Docker Desktop shares the local image store with its cluster.
  kubectl apply -f "$INGRESS_NGINX"
  # Docker Desktop's load balancer only serves one LoadBalancer service (the
  # API), so the ingress controller runs as NodePort and is port-forwarded.
  kubectl -n ingress-nginx patch svc ingress-nginx-controller \
    -p '{"spec":{"type":"NodePort","externalTrafficPolicy":"Cluster"}}'
  kubectl -n ingress-nginx wait --for=condition=ready pod \
    -l app.kubernetes.io/component=controller --timeout=300s
  kubectl apply -f "$METRICS_SERVER"
  kubectl -n kube-system patch deploy metrics-server --type=json \
    -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]' || true
fi

echo ">> applying API manifests"
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-deployment.yaml -f k8s/02-service.yaml -f k8s/04-hpa.yaml
# the ingress admission webhook needs a few seconds after the controller starts
for i in $(seq 1 20); do kubectl apply -f k8s/03-ingress.yaml && break; sleep 6; done

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
kubectl -n "$NS" rollout status deployment/heart-risk-api --timeout=300s
kubectl -n "$NS" rollout status deployment/prometheus --timeout=300s
kubectl -n "$NS" rollout status deployment/grafana --timeout=300s
kubectl -n "$NS" get pods,svc,ingress,hpa

cat <<EOF

Access (Docker Desktop):
  LoadBalancer : curl http://localhost:8080/health
  Ingress      : kubectl -n ingress-nginx port-forward svc/ingress-nginx-controller 8088:80
                 curl -H "Host: heart-risk.local" http://localhost:8088/health
  Prometheus   : kubectl -n $NS port-forward svc/prometheus 9090:9090
  Grafana      : kubectl -n $NS port-forward svc/grafana 3000:3000   (admin / admin)
  Traffic      : python scripts/load_test.py --url http://127.0.0.1:8080 -n 500
Minikube: run 'minikube tunnel' and use the EXTERNAL-IP of svc/heart-risk-api.
EOF
