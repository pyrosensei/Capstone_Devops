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
6. Applies `kubernetes/overlays/dev` with retries.
7. Waits for API and worker rollouts.

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
| Secret `devplane-secrets` | JWT key and bootstrap passwords |
| PVC `devplane-data` | SQLite data for the demo |
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

**SQLite warning:** the demo stores data on a ReadWriteOnce PVC. Multiple API pods on one kind node can share it, but this is not a production data pattern. Use PostgreSQL and a proper ReadWriteMany/database service before scaling across nodes.

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
helm lint helm/devplane
helm template devplane helm/devplane
helm upgrade --install devplane helm/devplane --namespace devplane --create-namespace
```

The chart creates its own Secret and ConfigMap. Set real values with `--set` or a values file; do not use the demo defaults in a shared environment.

## Cleanup

```powershell
kubectl delete -k kubernetes/overlays/dev --ignore-not-found
kind delete cluster --name devplane-kind
```
