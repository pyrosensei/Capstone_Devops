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
kubectl -n ingress-nginx wait --for=condition=complete job/ingress-nginx-admission-create --timeout=120s
kubectl -n ingress-nginx wait --for=condition=Ready pod -l app.kubernetes.io/component=controller --timeout=180s

echo "Installing metrics-server..."
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl -n kube-system patch deployment metrics-server --type=json \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]' || true
kubectl -n kube-system rollout status deployment/metrics-server --timeout=180s

docker build -t devplane-api:local .
kind load docker-image devplane-api:local --name "$CLUSTER"

applied=false
for attempt in 1 2 3 4 5; do
  if kubectl apply -k kubernetes/overlays/dev; then
    applied=true
    break
  fi
  echo "kubectl apply failed (attempt $attempt); retrying in 5s..." >&2
  sleep 5
done
if [ "$applied" != true ]; then
  echo "kubectl apply failed after 5 attempts" >&2
  exit 1
fi

echo "Generating application secret..."
SECRET_KEY=$(head -c 48 /dev/urandom | base64 | tr -d '\n')
kubectl -n devplane create secret generic devplane-secrets \
  --from-literal=SECRET_KEY="$SECRET_KEY" \
  --from-literal=BOOTSTRAP_ADMIN_PASSWORD=admin123 \
  --from-literal=BOOTSTRAP_DEV_PASSWORD=dev123 \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n devplane rollout restart deploy/devplane-api deploy/devplane-worker

kubectl -n devplane rollout status deploy/devplane-api --timeout=240s
kubectl -n devplane rollout status deploy/devplane-worker --timeout=240s

echo
echo "Cluster ready."
echo "Add '127.0.0.1 devplane.local' to /etc/hosts, then open http://devplane.local:8081"
echo "Or run: kubectl -n devplane port-forward svc/devplane-api 8000:80"
