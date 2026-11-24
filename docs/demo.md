# Demo and viva script

This walkthrough takes about 10–15 minutes. Use the Python and SQLite demo for a laptop presentation. The Compose and kind commands are for demonstrating the infrastructure separately.

## Hosted browser walkthrough

Open the HTTPS URL provided by the project owner and sign in with the developer credentials shared privately. The hosted service and its URL are pending verification.

1. Open **Catalog** and create a service with a unique name such as `checkout-demo` and a repository URL such as `https://github.com/example/checkout-api`.
2. Open **Delivery**, select your service, and create an ephemeral environment named `review-preview`. Refresh status until it shows `running`.
3. Release `v1.0.0` with the rolling strategy. Wait for success, then release `v2.0.0` with blue-green. Use the rollback action on `v2.0.0` and refresh to see `v1.0.0` restored in a new history entry.
4. Open **Flags & secrets**, select your service, and add an enabled `new-checkout` flag. Sign out and back in to see the saved changes.

Preview provisioning, releases, and rollback simulate execution. PostgreSQL stores their state, the release history, flags, and audit events. A private admin account can verify the audit log.

## 0. Prepare

From the repository root, activate the Python 3.11 environment and start the local demo:

```powershell
conda activate capstone_devops
python -m scripts.local_demo
```

Compose:

```powershell
docker compose up --build -d api worker redis
docker compose ps
```

Kubernetes:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/kind-up.ps1
kubectl -n devplane get pods,pvc,hpa,ingress
kubectl -n devplane port-forward svc/devplane-api 8001:80
```

Use <http://127.0.0.1:8000> for local/Compose or <http://127.0.0.1:8001> for the port-forward.

For the PowerShell examples below, set `$baseUrl` to the running server:

```powershell
$baseUrl = 'http://127.0.0.1:8000'
```

## 1. Log in

- Admin: `admin@devplane.local` / `admin123`
- Developer: `dev@devplane.local` / `dev123`

These are demo-only credentials. They are accepted only while `DEMO_MODE=true`
(the local demo, the dev overlay and the Helm dev values); outside demo mode
the password guard rejects them and requires the generated bootstrap passwords.

Show the seeded roles and the UI/API split.

## 2. Create a service

In the UI or with the API:

```powershell
$token = (Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/auth/login" `
  -Body @{username='admin@devplane.local'; password='admin123'}).access_token
$headers = @{Authorization = "Bearer $token"}
$service = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/services" `
  -Headers $headers -ContentType 'application/json' `
  -Body '{"name":"checkout-api","description":"Checkout service","repo_url":"https://github.com/example/checkout-api","tech_stack":"FastAPI"}'
$service
```

Point out repository URL validation, ownership, and the audit event.

## 3. Create an ephemeral environment

```powershell
$preview = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/services/$($service.id)/environments" `
  -Headers $headers -ContentType 'application/json' `
  -Body '{"name":"pr-42","env_type":"ephemeral","ttl_minutes":15}'
$preview
```

Show `provisioning -> running`, `expires_at`, and the duplicate-name `409` behavior.

## 4. Deploy and roll back

```powershell
$dep1 = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/environments/$($preview.id)/deployments" `
  -Headers $headers -ContentType 'application/json' `
  -Body '{"version":"v1.0.0","strategy":"rolling"}'
Start-Sleep -Seconds 4
$dep2 = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/environments/$($preview.id)/deployments" `
  -Headers $headers -ContentType 'application/json' `
  -Body '{"version":"v2.0.0","strategy":"blue-green"}'
Start-Sleep -Seconds 4
Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/deployments/$($dep2.id)/rollback" -Headers $headers
```

Use **Refresh status** in the Delivery tab to show the status transitions and the rollback to `v1.0.0`. The version history and strategy labels represent simulated execution.

## 5. Feature flag and secret reference

```powershell
Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/services/$($service.id)/flags" `
  -Headers $headers -ContentType 'application/json' `
  -Body '{"key":"new-checkout","enabled":true,"description":"Checkout v2"}'
Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/services/$($service.id)/secrets" `
  -Headers $headers -ContentType 'application/json' `
  -Body '{"name":"stripe-key","provider":"kubernetes","ref_path":"devplane/stripe-key"}'
```

Emphasize that only the reference path is stored.

## 6. Ops registry

Open the Ops panel or call:

```powershell
Invoke-RestMethod "$baseUrl/api/v1/ops/tools" -Headers $headers
Invoke-RestMethod "$baseUrl/api/v1/ops/pods?namespace=devplane" -Headers $headers
```

- Local/Compose without a kubeconfig: `source: stub`.
- Kubernetes: `source: kubernetes`.

Being explicit about the source is part of the design.

## 7. Admin metrics and audit

```powershell
Invoke-RestMethod "$baseUrl/api/v1/admin/metrics" -Headers $headers
Invoke-RestMethod "$baseUrl/api/v1/admin/audit?limit=10" -Headers $headers
```

Show environment counts, deployment counts, active users, flags, secret references, and audit entries. Try to update/delete an audit row through the ORM and explain the immutability guard.

## 8. TTL reaper

```powershell
Invoke-RestMethod -Method Post "$baseUrl/api/v1/admin/maintenance/expire-environments" -Headers $headers
```

Expired environments become `terminated`. Compose and kind also run the reaper from the worker every few seconds.

## 9. Metrics and health

```powershell
Invoke-WebRequest -UseBasicParsing "$baseUrl/health"
Invoke-WebRequest -UseBasicParsing "$baseUrl/health/ready"
```

Point out `X-Request-ID` and structured JSON logs. If you configured `METRICS_TOKEN`, use that token as a Bearer credential to show the `devplane_*` metrics at `/metrics`.

## 10. Automated proof

```powershell
conda run -n capstone_devops pytest --cov=app --cov-report=term-missing
conda run -n capstone_devops ruff check app tests worker
python scripts/smoke.py --base-url $baseUrl --skip-metrics
```

For Kubernetes, use the port-forward URL:

```powershell
conda run -n capstone_devops python scripts/smoke.py --base-url http://127.0.0.1:8001
```

## Evidence checklist

Capture:

- UI login and catalog.
- Environment and deployment status.
- Rollback entry.
- Feature flag/secret reference.
- Ops registry with `source: kubernetes`.
- Admin metrics and audit log.
- `docker compose ps`.
- `kubectl -n devplane get pods,pvc,hpa,ingress`.
- Jenkins pipeline (if available).
- Grafana dashboard and Loki logs.
- SonarQube project (if available).
- Argo CD synced application (if available).

Save them under `docs/screenshots/`.
