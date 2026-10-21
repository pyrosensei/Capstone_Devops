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

kubectl create namespace devplane --dry-run=client -o yaml | kubectl apply -f -

get_secret_value() {
  local encoded
  encoded=$(kubectl -n devplane get secret devplane-secrets -o jsonpath="{.data.$1}" 2>/dev/null || true)
  if [ -z "$encoded" ]; then
    return 0
  fi
  printf '%s' "$encoded" | base64 -d
}

SECRET_KEY=$(get_secret_value SECRET_KEY)
if [ -z "$SECRET_KEY" ]; then
  SECRET_KEY=$(head -c 48 /dev/urandom | base64 | tr -d '\n')
fi
POSTGRES_PASSWORD=$(get_secret_value POSTGRES_PASSWORD)
if [ -z "$POSTGRES_PASSWORD" ]; then
  POSTGRES_PASSWORD=$(head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n')
fi
BOOTSTRAP_ADMIN_PASSWORD=$(get_secret_value BOOTSTRAP_ADMIN_PASSWORD)
BOOTSTRAP_ADMIN_PASSWORD=${BOOTSTRAP_ADMIN_PASSWORD:-admin123}
BOOTSTRAP_DEV_PASSWORD=$(get_secret_value BOOTSTRAP_DEV_PASSWORD)
BOOTSTRAP_DEV_PASSWORD=${BOOTSTRAP_DEV_PASSWORD:-dev123}
DATABASE_URL="postgresql+psycopg2://devplane:${POSTGRES_PASSWORD}@devplane-postgres:5432/devplane"

kubectl -n devplane create secret generic devplane-secrets \
  --from-literal=SECRET_KEY="$SECRET_KEY" \
  --from-literal=POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  --from-literal=DATABASE_URL="$DATABASE_URL" \
  --from-literal=BOOTSTRAP_ADMIN_PASSWORD="$BOOTSTRAP_ADMIN_PASSWORD" \
  --from-literal=BOOTSTRAP_DEV_PASSWORD="$BOOTSTRAP_DEV_PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -

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

kubectl -n devplane rollout restart deploy/devplane-api deploy/devplane-worker

kubectl -n devplane rollout status deploy/devplane-postgres --timeout=240s
kubectl -n devplane rollout status deploy/devplane-api --timeout=240s
kubectl -n devplane rollout status deploy/devplane-worker --timeout=240s

echo
echo "Cluster ready."
echo "Add '127.0.0.1 devplane.local' to /etc/hosts, then open http://devplane.local:8081"
echo "Or run: kubectl -n devplane port-forward svc/devplane-api 8000:80"
