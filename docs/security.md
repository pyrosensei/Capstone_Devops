# Security notes

## Identity and access

- Local JWT authentication with HS256 signing and a configurable `SECRET_KEY`.
- Roles: `admin` and `developer`.
- Developers can manage catalog entries, environments, deployments, flags, and secret references.
- Admin-only: service deletion, deployment status override, audit log, platform metrics, and the manual TTL reaper.
- Bootstrap accounts are seeded for the demo. Change `BOOTSTRAP_ADMIN_PASSWORD` and `BOOTSTRAP_DEV_PASSWORD` before any shared environment.
- Registration accepts internal `.local` addresses for the offline demo; this is a deliberate validation exception.

The demo does not include OIDC/SSO, MFA, refresh-token rotation, or account lockout. Those are listed as future work.

## Secrets

- `.env` is ignored by Git; `.env.example` contains placeholders only.
- Kubernetes Secrets hold the JWT key and bootstrap passwords.
- The API's secret-reference feature stores provider and path metadata, not secret values.
- Compose defaults are demo values and must be overridden.
- The repository includes no registry, Sonar, Slack, Jenkins, or cloud credentials.

For production, use an external secret store (Vault, AWS Secrets Manager, Azure Key Vault) and a controller such as External Secrets Operator rather than plain Kubernetes Secrets.

## Containers

- Multi-stage build keeps compilers and build dependencies out of the runtime image.
- Runtime user `10001` with no login shell.
- Kubernetes pod security context:
  - `runAsNonRoot: true`
  - `readOnlyRootFilesystem: true`
  - `allowPrivilegeEscalation: false`
  - all capabilities dropped
  - `seccompProfile: RuntimeDefault`
- Writable paths are limited to the data PVC and an emptyDir `/tmp`.
- The image runs Alembic only when `RUN_MIGRATIONS=1`.

## Kubernetes

- `kubernetes/base/rbac.yaml` grants the service account only the reads needed by the ops registry (pods, logs, deployments).
- `kubernetes/base/poddisruptionbudget.yaml` protects API availability.
- `kubernetes/security/networkpolicy.yaml` is an optional policy; apply it deliberately because it can block DNS/Redis/ingress depending on your cluster CNI.
- Ingress and Services are internal by default; expose them only through the intended ingress controller.
- The demo uses an RWO PVC with SQLite. This is not suitable for multi-node production.

## Supply chain and scanning

- Jenkins runs Ruff before tests.
- Optional SonarQube stage when `SONAR_HOST_URL` is configured.
- Optional Trivy image scan in Jenkins (report-only by default).
- `pip-audit` can be run locally:

```powershell
conda run -n capstone_devops pip install pip-audit
conda run -n capstone_devops pip-audit -r requirements.txt
```

- The Dockerfile uses official base images. Pin digests for stricter reproducibility.
- Add Cosign signing and SBOM generation before publishing production images.

## Audit trail

- Audit rows are append-only at the ORM level through `before_update` and `before_delete` listeners.
- Events record actor, action, entity, detail, timestamp, and sequence.
- Admin audit access is role-restricted.
- Database-level immutability (revoked UPDATE/DELETE grants or append-only storage) is a future hardening step.

## Network and transport

- TLS is not terminated inside the application. Add TLS at the ingress controller or a load balancer.
- CORS origins are configurable and default to localhost.
- Redis has no password in the local Compose file. Do not expose it beyond the demo network.
- The Jenkins Docker socket mount is powerful; use it only in an isolated demo.

## Demo hardening checklist

1. Replace `SECRET_KEY` and both bootstrap passwords.
2. Change the Grafana admin password.
3. Set a PostgreSQL password if using the override.
4. Keep `.env` out of Git.
5. Apply the NetworkPolicy only after checking cluster DNS and ingress behavior.
6. Set `--exit-code 1` for Trivy if the pipeline must block vulnerabilities.
7. Remove demo users/data before publishing screenshots or recordings.

## Residual risks

- Local JWT without SSO or MFA.
- Well-known demo credentials if not changed.
- SQLite concurrency and single-node storage assumptions.
- Simulated provisioning/deployment rather than a hardened executor.
- Optional scanners and policies are not enabled by default.
