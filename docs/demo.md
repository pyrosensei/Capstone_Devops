# Demo and viva script

This walkthrough takes about 10-15 minutes. Choose one runtime: local API, Docker Compose, or kind.

## 0. Prepare

Local:

```powershell
conda activate capstone_devops
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
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

## 1. Log in

- Admin: `admin@devplane.local` / `admin123`
- Developer: `dev@devplane.local` / `dev123`

Show the seeded roles and the UI/API split.

## 2. Create a service

In the UI or with the API:

```powershell
$token = (Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/auth/login `
  -Body @{username='admin@devplane.local'; password='admin123'}).access_token
$headers = @{Authorization = "Bearer $token"}
$service = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/services `
  -Headers $headers -ContentType 'application/json' `
  -Body '{"name":"payments-api","description":"Payments service","repo_url":"https://github.com/example/payments-api","tech_stack":"FastAPI"}'
$service
```

Point out repository URL validation, ownership, and the audit event.

## 3. Create an ephemeral environment

```powershell
$env = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/services/$($service.id)/environments" `
  -Headers $headers -ContentType 'application/json' `
  -Body '{"name":"pr-42","env_type":"ephemeral","ttl_minutes":15}'
$env
```

Show `provisioning -> running`, `expires_at`, and the duplicate-name `409` behavior.

## 4. Deploy and roll back

```powershell
$dep1 = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/environments/$($env.id)/deployments" `
  -Headers $headers -ContentType 'application/json' `
  -Body '{"version":"v1.0.0","strategy":"rolling"}'
Start-Sleep -Seconds 3
$dep2 = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/environments/$($env.id)/deployments" `
  -Headers $headers -ContentType 'application/json' `
  -Body '{"version":"v2.0.0","strategy":"blue-green"}'
Start-Sleep -Seconds 3
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/deployments/$($dep2.id)/rollback" -Headers $headers
```

Show the deployment history, status transitions, strategy values, and rollback record.

## 5. Feature flag and secret reference

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/services/$($service.id)/flags" `
  -Headers $headers -ContentType 'application/json' `
  -Body '{"key":"new-checkout","enabled":true,"description":"Checkout v2"}'
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/services/$($service.id)/secrets" `
  -Headers $headers -ContentType 'application/json' `
  -Body '{"name":"stripe-key","provider":"kubernetes","ref_path":"devplane/stripe-key"}'
```

Emphasize that only the reference path is stored.

## 6. Ops registry

Open the Ops panel or call:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/ops/tools" -Headers $headers
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/ops/pods?namespace=devplane" -Headers $headers
```

- Local/Compose without a kubeconfig: `source: stub`.
- Kubernetes: `source: kubernetes`.

Being explicit about the source is part of the design.

## 7. Admin metrics and audit

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/admin/metrics" -Headers $headers
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/admin/audit?limit=10" -Headers $headers
```

Show environment counts, deployment counts, active users, flags, secret references, and audit entries. Try to update/delete an audit row through the ORM and explain the immutability guard.

## 8. TTL reaper

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/api/v1/admin/maintenance/expire-environments" -Headers $headers
```

The worker also runs the reaper every few seconds. Expired environments become `terminated`.

## 9. Metrics and health

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health/ready
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/metrics
```

Point out `X-Request-ID`, structured JSON logs, and `devplane_*` metrics.

## 10. Automated proof

```powershell
conda run -n capstone_devops pytest --cov=app --cov-report=term-missing
conda run -n capstone_devops ruff check app tests worker
conda run -n capstone_devops python scripts/smoke.py --base-url http://127.0.0.1:8000
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
