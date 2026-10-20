#!/usr/bin/env bash
set -euo pipefail

CLUSTER=devplane-kind

command -v docker >/dev/null || { echo "Docker is required"; exit 1; }
command -v kind >/dev/null || { echo "Install kind from https://kind.sigs.k8s.io/"; exit 1; }
command -v kubectl >/dev/null || { echo "Install kubectl"; exit 1; }

if ! kind get clusters | grep -qx "$CLUSTER"; then
  kind create cluster --name "$CLUSTER" --config kubernetes/kind-config.yaml
fi

echo "Installing ingress-nginx..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl -n ingress-nginx wait --for=condition=Available deployment/ingress-nginx-controller --timeout=240s

echo "Installing metrics-server..."
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl -n kube-system patch deployment metrics-server --type=json \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]' || true
kubectl -n kube-system rollout status deployment/metrics-server --timeout=180s

docker build -t devplane-api:local .
kind load docker-image devplane-api:local --name "$CLUSTER"

kubectl apply -k kubernetes/overlays/dev
kubectl -n devplane rollout status deploy/devplane-api --timeout=240s
kubectl -n devplane rollout status deploy/devplane-worker --timeout=240s

echo
echo "Cluster ready."
echo "Add '127.0.0.1 devplane.local' to /etc/hosts, then open http://devplane.local:8081"
echo "Or run: kubectl -n devplane port-forward svc/devplane-api 8000:80"
