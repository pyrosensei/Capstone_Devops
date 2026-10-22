#!/usr/bin/env bash
# Installs Argo CD into the current Kubernetes cluster and applies the
# DevPlane Application. Everything is pinned to a released version.
#
# Usage: ./scripts/argocd-up.sh
set -euo pipefail

ARGOCD_VERSION="v3.5.6"
MANIFEST="https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/install.yaml"
NAMESPACE="argocd"

command -v kubectl >/dev/null || { echo "kubectl is required"; exit 1; }

echo "Creating namespace ${NAMESPACE}..."
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

echo "Installing Argo CD ${ARGOCD_VERSION}..."
kubectl apply -n "${NAMESPACE}" -f "${MANIFEST}"

# The ApplicationSet CRD is larger than the annotation limit of the API
# server, so it has to be applied with server-side apply.
curl -fsSL "https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/crds/applicationset-crd.yaml" \
  -o /tmp/argocd-applicationset-crd.yaml
kubectl apply --server-side -f /tmp/argocd-applicationset-crd.yaml

echo "Waiting for the Argo CD control plane..."
kubectl -n "${NAMESPACE}" rollout status deploy/argocd-server --timeout=300s
kubectl -n "${NAMESPACE}" rollout status deploy/argocd-repo-server --timeout=300s
kubectl -n "${NAMESPACE}" rollout status statefulset/argocd-application-controller --timeout=300s

echo "Applying the DevPlane Application..."
kubectl apply -f gitops/argocd/application.yaml

echo
echo "Argo CD is installed. Open the UI with:"
echo "  kubectl -n argocd port-forward svc/argocd-server 8090:80"
echo
echo "Set a known admin password (the secret stores a bcrypt hash):"
echo "  kubectl -n argocd exec deploy/argocd-server -- argocd account bcrypt --password '<your-password>'"
echo "Check the sync state with: kubectl -n argocd get applications"
