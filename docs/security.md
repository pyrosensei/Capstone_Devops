# Security notes (Phase 9)

- Non-root container user `10001` in the Dockerfile and pod `securityContext`.
- Secrets live in Kubernetes Secrets / `.env`, never in source. Secret *references* in the API store a path, not a value.
- JWT signing key from `SECRET_KEY`.
- Role-based access: `developer` vs `admin` (delete catalog + admin metrics).
- Jenkins should inject registry and Sonar tokens via Credentials Binding.
- Optional SonarQube scan in `Jenkinsfile` when `SONAR_HOST_URL` is set.
- Dependency scanning: `pip install pip-audit && pip-audit -r requirements.txt`.
- RBAC Role `devplane-ops` limits the in-cluster client to get/list pods, logs, and deployments.
- Change bootstrap passwords before any shared demo.
