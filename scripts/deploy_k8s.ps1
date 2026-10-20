# Windows PowerShell equivalent of scripts/deploy_k8s.sh
#   powershell -ExecutionPolicy Bypass -File scripts\deploy_k8s.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$IMAGE = "heart-risk-api:1.0.0"
$NS = "heart-risk"
$INGRESS_NGINX = "https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.12.1/deploy/static/provider/cloud/deploy.yaml"
$METRICS_SERVER = "https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.7.2/components.yaml"
$CTX = kubectl config current-context
Write-Host ">> kube context: $CTX"

docker build -t $IMAGE .

if ($CTX -eq "minikube") {
    minikube image load $IMAGE
    minikube addons enable ingress | Out-Null
    minikube addons enable metrics-server | Out-Null
} else {
    kubectl apply -f $INGRESS_NGINX
    kubectl -n ingress-nginx patch svc ingress-nginx-controller -p '{\"spec\":{\"type\":\"NodePort\",\"externalTrafficPolicy\":\"Cluster\"}}'
    kubectl -n ingress-nginx wait --for=condition=ready pod -l app.kubernetes.io/component=controller --timeout=300s
    kubectl apply -f $METRICS_SERVER
    kubectl -n kube-system patch deploy metrics-server --type=json -p '[{\"op\":\"add\",\"path\":\"/spec/template/spec/containers/0/args/-\",\"value\":\"--kubelet-insecure-tls\"}]'
}

kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-deployment.yaml -f k8s/02-service.yaml -f k8s/04-hpa.yaml
for ($i = 0; $i -lt 20; $i++) {
    kubectl apply -f k8s/03-ingress.yaml
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep -Seconds 6
}

kubectl -n $NS create configmap prometheus-rules --from-file=monitoring/alert_rules.yml --dry-run=client -o yaml | kubectl apply -f -
$ds = (Get-Content monitoring/grafana/provisioning/datasources/datasource.yml -Raw) -replace "http://prometheus:9090", "http://prometheus.heart-risk.svc:9090"
$tmp = New-TemporaryFile
Set-Content -Path $tmp -Value $ds
kubectl -n $NS create configmap grafana-datasources --from-file=datasource.yml=$tmp --dry-run=client -o yaml | kubectl apply -f -
kubectl -n $NS create configmap grafana-dashboard-provider --from-file=monitoring/grafana/provisioning/dashboards/dashboards.yml --dry-run=client -o yaml | kubectl apply -f -
kubectl -n $NS create configmap grafana-dashboards --from-file=monitoring/grafana/dashboards/heart-risk-api.json --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f k8s/monitoring/

kubectl -n $NS rollout status deployment/heart-risk-api --timeout=300s
kubectl -n $NS rollout status deployment/prometheus --timeout=300s
kubectl -n $NS rollout status deployment/grafana --timeout=300s
kubectl -n $NS get pods,svc,ingress,hpa
Write-Host "`nLoadBalancer: http://localhost:8080   Ingress: kubectl -n ingress-nginx port-forward svc/ingress-nginx-controller 8088:80"
Write-Host "Grafana: kubectl -n $NS port-forward svc/grafana 3000:3000   Prometheus: kubectl -n $NS port-forward svc/prometheus 9090:9090"
