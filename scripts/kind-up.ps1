$ErrorActionPreference = "Continue"
$cluster = "devplane-kind"

function Assert-ExitCode([string]$step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$step failed with exit code $LASTEXITCODE"
    }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is required. Install Docker Desktop and start it."
}
if (-not (Get-Command kind -ErrorAction SilentlyContinue)) {
    throw "kind is required. Install with: winget install Kubernetes.kind"
}
if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    throw "kubectl is required. Install with: winget install Kubernetes.kubectl"
}

$existing = @(kind get clusters 2>$null | Where-Object { $_ -and $_ -notmatch "No kind clusters found" })
if ($existing -notcontains $cluster) {
    Write-Host "Creating kind cluster '$cluster'..."
    kind create cluster --name $cluster --config kubernetes/kind-config.yaml
    Assert-ExitCode "kind create cluster"
} else {
    Write-Host "Reusing kind cluster '$cluster'."
}

Write-Host "Installing ingress-nginx..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
Assert-ExitCode "install ingress-nginx"
kubectl -n ingress-nginx wait --for=condition=Available deployment/ingress-nginx-controller --timeout=240s
Assert-ExitCode "wait for ingress-nginx"
kubectl -n ingress-nginx wait --for=condition=complete job/ingress-nginx-admission-create --timeout=120s
Assert-ExitCode "wait for ingress admission certificate"
kubectl -n ingress-nginx wait --for=condition=Ready pod -l app.kubernetes.io/component=controller --timeout=180s
Assert-ExitCode "wait for ingress admission webhook"

Write-Host "Installing metrics-server (required for HPA)..."
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
Assert-ExitCode "install metrics-server"
$patched = kubectl get deployment metrics-server -n kube-system -o jsonpath="{.spec.template.spec.containers[0].args}" | Select-String -SimpleMatch "--kubelet-insecure-tls"
if (-not $patched) {
    kubectl -n kube-system patch deployment metrics-server --type=json --patch-file kubernetes/metrics-server-patch.json
    Assert-ExitCode "patch metrics-server"
}
kubectl -n kube-system rollout status deployment/metrics-server --timeout=180s
Assert-ExitCode "wait for metrics-server"

Write-Host "Building and loading DevPlane image..."
docker build -t devplane-api:local .
Assert-ExitCode "docker build"
kind load docker-image devplane-api:local --name $cluster
Assert-ExitCode "kind load docker-image"

Write-Host "Applying Kubernetes manifests..."
$applied = $false
for ($attempt = 1; $attempt -le 5; $attempt++) {
    kubectl apply -k kubernetes/overlays/dev
    if ($LASTEXITCODE -eq 0) {
        $applied = $true
        break
    }
    if ($attempt -lt 5) {
        Write-Host "Apply failed (attempt $attempt); retrying in 5s..."
        Start-Sleep -Seconds 5
    }
}
if (-not $applied) {
    throw "kubectl apply failed after 5 attempts"
}
kubectl -n devplane rollout status deploy/devplane-api --timeout=240s
Assert-ExitCode "api rollout"
kubectl -n devplane rollout status deploy/devplane-worker --timeout=240s
Assert-ExitCode "worker rollout"

Write-Host ""
Write-Host "Cluster ready."
Write-Host "Add this line to C:\Windows\System32\drivers\etc\hosts (as Administrator):"
Write-Host "  127.0.0.1 devplane.local"
Write-Host "Then open: http://devplane.local:8081"
Write-Host "Or run:  kubectl -n devplane port-forward svc/devplane-api 8000:80"
