# Installs Argo CD into the current Kubernetes cluster and applies the
# DevPlane Application. Everything is pinned to a released version.
#
# Usage: powershell -ExecutionPolicy Bypass -File scripts/argocd-up.ps1

$ErrorActionPreference = "Continue"
$argocdVersion = "v3.5.6"
$manifest = "https://raw.githubusercontent.com/argoproj/argo-cd/$argocdVersion/manifests/install.yaml"
$namespace = "argocd"

function Assert-ExitCode([string]$step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$step failed with exit code $LASTEXITCODE"
    }
}

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    throw "kubectl is required."
}

Write-Host "Creating namespace $namespace..."
kubectl create namespace $namespace --dry-run=client -o yaml | kubectl apply -f -
Assert-ExitCode "create namespace"

Write-Host "Installing Argo CD $argocdVersion..."
kubectl apply -n $namespace -f $manifest
Assert-ExitCode "install argocd"

# The ApplicationSet CRD is larger than the annotation limit of the API
# server, so it has to be applied with server-side apply.
$crd = Join-Path $env:TEMP "argocd-applicationset-crd.yaml"
try {
    Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/argoproj/argo-cd/$argocdVersion/manifests/crds/applicationset-crd.yaml" -OutFile $crd
    kubectl apply --server-side -f $crd
    Assert-ExitCode "apply applicationset crd"
} catch {
    Write-Host "Could not refresh the ApplicationSet CRD: $($_.Exception.Message)"
}

Write-Host "Waiting for the Argo CD control plane..."
kubectl -n $namespace rollout status deploy/argocd-server --timeout=300s
Assert-ExitCode "wait for argocd-server"
kubectl -n $namespace rollout status deploy/argocd-repo-server --timeout=300s
Assert-ExitCode "wait for argocd-repo-server"
kubectl -n $namespace rollout status statefulset/argocd-application-controller --timeout=300s
Assert-ExitCode "wait for argocd-application-controller"

Write-Host "Applying the DevPlane Application..."
kubectl apply -f gitops/argocd/application.yaml
Assert-ExitCode "apply application"

Write-Host ""
Write-Host "Argo CD is installed. Open the UI with:"
Write-Host "  kubectl -n argocd port-forward svc/argocd-server 8090:80"
Write-Host ""
Write-Host "Set a known admin password (the secret stores a bcrypt hash):"
Write-Host "  kubectl -n argocd exec deploy/argocd-server -- argocd account bcrypt --password '<your-password>'"
Write-Host "  kubectl -n argocd patch secret argocd-secret --type merge -p '{\"stringData\":{\"admin.password\":\"<bcrypt-hash>\",\"admin.passwordMtime\":\"<rfc3339>\"}}'"
Write-Host "  kubectl -n argocd rollout restart deploy/argocd-server"
Write-Host ""
Write-Host "Check the sync state with:"
Write-Host "  kubectl -n argocd get applications"
