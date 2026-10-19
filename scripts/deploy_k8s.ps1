# Windows PowerShell equivalent of scripts/deploy_k8s.sh
#   powershell -ExecutionPolicy Bypass -File scripts\deploy_k8s.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$IMAGE = "heart-risk-api:1.0.0"
$NS = "heart-risk"

docker build -t $IMAGE .
minikube image load $IMAGE
minikube addons enable ingress | Out-Null

kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-deployment.yaml -f k8s/02-service.yaml -f k8s/03-ingress.yaml
kubectl apply -f k8s/04-hpa.yaml

kubectl -n $NS create configmap prometheus-rules --from-file=monitoring/alert_rules.yml --dry-run=client -o yaml | kubectl apply -f -
$ds = (Get-Content monitoring/grafana/provisioning/datasources/datasource.yml -Raw) -replace "http://prometheus:9090", "http://prometheus.heart-risk.svc:9090"
$tmp = New-TemporaryFile
Set-Content -Path $tmp -Value $ds
kubectl -n $NS create configmap grafana-datasources --from-file=datasource.yml=$tmp --dry-run=client -o yaml | kubectl apply -f -
kubectl -n $NS create configmap grafana-dashboard-provider --from-file=monitoring/grafana/provisioning/dashboards/dashboards.yml --dry-run=client -o yaml | kubectl apply -f -
kubectl -n $NS create configmap grafana-dashboards --from-file=monitoring/grafana/dashboards/heart-risk-api.json --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f k8s/monitoring/

kubectl -n $NS rollout status deployment/heart-risk-api --timeout=180s
kubectl -n $NS get pods,svc,ingress
Write-Host "`nRun 'minikube tunnel' in another terminal, then use the EXTERNAL-IP of svc/heart-risk-api."
