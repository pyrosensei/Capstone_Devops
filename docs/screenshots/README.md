# Screenshots

These are real captures from the running DevPlane stack, produced by
`scripts/capture_screenshots.py` (Playwright, headless Chromium). Re-create
them with:

```powershell
# cluster UI (kind) and the observability stack
kubectl -n devplane port-forward svc/devplane-api 8001:80
docker compose --profile observability up -d prometheus grafana
conda run -n capstone_devops python scripts/capture_screenshots.py `
    --devplane-url http://127.0.0.1:8001 `
    --grafana-url http://127.0.0.1:3000 `
    --prometheus-url http://127.0.0.1:9090 `
    --argocd-url https://127.0.0.1:8090
```

| File | What it shows |
| --- | --- |
| `ui-login.png` | DevPlane login screen with the demo credentials |
| `ui-catalog.png` | Service catalog after signing in as admin |
| `deployment-history.png` | Delivery tab: environments, deployments, rollback |
| `feature-flags.png` | Feature flags and secret references (paths only) |
| `ops-registry.png` | Ops registry reading the live kind cluster (`source: kubernetes`) |
| `admin-audit.png` | Admin metrics and the append-only audit trail |
| `grafana-dashboard.png` | "DevPlane Control Plane" Grafana dashboard |
| `prometheus-targets.png` | Prometheus targets - the `/metrics` scrape is `up` with the bearer token |
| `argocd-applications.png` | Argo CD: Application `devplane` from the real repository, `Synced` |

## Still missing

- `jenkins-pipeline.png` - needs a Jenkins controller (Docker). The local
  controller recipe is in `docs/jenkins-setup.md`; the capture is pending
  because Docker was paused during the last session.
- `sonar.png` - needs a SonarQube server (Docker Compose `security` profile).
- `loki-logs.png` - can be captured from the Loki UI at
  <http://127.0.0.1:3100> once the observability profile is running.
- `docker-ps.png` - `docker compose ps` output.
- `k8s-pods.png` - `kubectl -n devplane get pods,pvc,hpa,ingress` output.
