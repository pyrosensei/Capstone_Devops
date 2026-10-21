# Kubernetes runbook

## Prerequisites

- Docker Desktop or Docker Engine
- `kind`
- `kubectl`
- Helm (optional, for the chart path)

On Windows the automated script expects `kind` and `kubectl` on `PATH`.

## One-command kind setup

```powershell
powershell -ExecutionPolicy Bypass -File scripts/kind-up.ps1
```

The script:

1. Creates `devplane-kind` from `kubernetes/kind-config.yaml` if it does not exist.
2. Maps ingress ports 80/443 to host ports 8081/8443.
3. Installs ingress-nginx and waits for its admission webhook.
4. Installs metrics-server and adds `--kubelet-insecure-tls` for kind.
5. Builds `devplane-api:local` and loads it into the node.
6. Creates the `devplane` namespace and the `devplane-secrets` Secret with a generated JWT key, PostgreSQL password, matching `DATABASE_URL`, and bootstrap passwords.
7. Applies `kubernetes/overlays/dev` with retries.
8. Waits for PostgreSQL, API, and worker rollouts. The API entrypoint runs `alembic upgrade head`; the migration takes a PostgreSQL advisory lock so concurrent replicas cannot race.

Linux/macOS: `./scripts/kind-up.sh`.

## Access

Add this line to the hosts file:

```text
127.0.0.1 devplane.local
```

Then open <http://devplane.local:8081>.

Without changing the hosts file:

```powershell
Invoke-WebRequest -UseBasicParsing -Headers @{Host='devplane.local'} http://127.0.0.1:8081/
```

Or port-forward:

```powershell
kubectl -n devplane port-forward svc/devplane-api 8001:80
```

Then use <http://127.0.0.1:8001> and run the smoke test with `--base-url http://127.0.0.1:8001`.

## What gets deployed

| Resource | Purpose |
| --- | --- |
| Namespace `devplane` | Isolation |
| ConfigMap `devplane-config` | Non-secret runtime configuration |
| Secret `devplane-secrets` | JWT key, PostgreSQL password, `DATABASE_URL`, bootstrap passwords (created by the script, not by Kustomize) |
| PVC `devplane-postgres-data` | PostgreSQL data |
| Deployment/Service `devplane-postgres` | PostgreSQL 16 backing store |
| Deployment `devplane-api` | FastAPI API, two replicas |
| Deployment `devplane-worker` | Provisioning/TTL worker |
| Deployment/Service `devplane-redis` | Redis |
| Services `devplane-api`, `-blue`, `-green` | Main and color-specific routing |
| Ingress `devplane` | NGINX host routing |
| HPA `devplane-api` | CPU-based scaling |
| PodDisruptionBudget | Minimum available API replicas |
| ServiceAccount/Role/RoleBinding | Read-only ops access |

## Probes

- **Startup**: `/health/live`, tolerant of slow first start.
- **Readiness**: `/health/ready`, checks the database.
- **Liveness**: `/health/live`, process-level only.

The worker does not serve HTTP, so it has no HTTP probe.

## Security context

Pods run as UID/GID `10001`, disallow privilege escalation, use a read-only root filesystem, mount `/tmp` as an emptyDir, drop all capabilities, and set seccomp `RuntimeDefault`.

## Scaling

```powershell
kubectl -n devplane get hpa
kubectl -n devplane scale deploy/devplane-api --replicas=3
```

The HPA needs metrics-server. The kind script installs it and adds `--kubelet-insecure-tls`.

**Database:** the demo uses a PostgreSQL Deployment with a ReadWriteOnce PVC. This is sufficient for the single-node kind demo; for production, use a managed PostgreSQL service (`externalDatabase.url` in Helm) or a highly available database.

## Delivery strategies

- Rolling update: default Deployment strategy.
- Blue-green: color labels plus `devplane-api-blue`/`devplane-api-green` Services.
- Canary: `kubernetes/overlays/canary`.

Commands and caveats: [deployment-strategy.md](deployment-strategy.md).

## Operations

```powershell
kubectl -n devplane get pods,pvc,svc,hpa,ingress
kubectl -n devplane describe pod <pod>
kubectl -n devplane logs deploy/devplane-api --tail=100
kubectl -n devplane rollout status deploy/devplane-api
kubectl -n devplane rollout undo deploy/devplane-api
```

Run the end-to-end smoke test:

```powershell
conda run -n capstone_devops python scripts/smoke.py --base-url http://127.0.0.1:8001
```

Inside the cluster, the API uses its ServiceAccount for ops calls. `GET /api/v1/ops/pods?namespace=devplane` should return `source: kubernetes`.

## Troubleshooting

### `ImagePullBackOff` for `devplane-api:local`

The image must exist inside the kind node:

```powershell
docker build -t devplane-api:local .
kind load docker-image devplane-api:local --name devplane-kind
kubectl -n devplane rollout restart deploy/devplane-api
```

### Ingress returns 503

Check that the API Service has endpoints and that the Ingress points to port 80:

```powershell
kubectl -n devplane get endpoints devplane-api
kubectl -n devplane describe ingress devplane
```

### `kubectl apply` fails on the ingress admission webhook

The controller or admission job may still be starting. Wait and retry:

```powershell
kubectl -n ingress-nginx wait --for=condition=Ready pod -l app.kubernetes.io/component=controller --timeout=180s
kubectl apply -k kubernetes/overlays/dev
```

### HPA shows `<unknown>` targets

Wait for metrics-server, then check:

```powershell
kubectl -n kube-system get pods -l k8s-app=metrics-server
kubectl top nodes
kubectl top pods -n devplane
```

### Port 8081 already in use

Change the host port in `kubernetes/kind-config.yaml` before creating the cluster, or use port-forward.

## Helm alternative

```powershell
$secret = python -c "import secrets; print(secrets.token_urlsafe(48))"
$pg = python -c "import secrets; print(secrets.token_urlsafe(24))"
$admin = python -c "import secrets; print(secrets.token_urlsafe(18))"
$dev = python -c "import secrets; print(secrets.token_urlsafe(18))"
helm lint helm/devplane --set-string secret.SECRET_KEY=$secret --set-string secret.POSTGRES_PASSWORD=$pg --set-string secret.BOOTSTRAP_ADMIN_PASSWORD=$admin --set-string secret.BOOTSTRAP_DEV_PASSWORD=$dev
helm template devplane helm/devplane --set-string secret.SECRET_KEY=$secret --set-string secret.POSTGRES_PASSWORD=$pg --set-string secret.BOOTSTRAP_ADMIN_PASSWORD=$admin --set-string secret.BOOTSTRAP_DEV_PASSWORD=$dev
helm upgrade --install devplane helm/devplane --namespace devplane --create-namespace --set-string secret.SECRET_KEY=$secret --set-string secret.POSTGRES_PASSWORD=$pg --set-string secret.BOOTSTRAP_ADMIN_PASSWORD=$admin --set-string secret.BOOTSTRAP_DEV_PASSWORD=$dev
```

The chart creates its own Secret and ConfigMap, PostgreSQL Deployment/PVC, Redis, API/worker, HPA, and Ingress. All four secret values are required and have no usable defaults. To use a managed database instead, set `postgresql.enabled=false` and provide `externalDatabase.url`.

## Cleanup

```powershell
kubectl delete -k kubernetes/overlays/dev --ignore-not-found
kind delete cluster --name devplane-kind
```
