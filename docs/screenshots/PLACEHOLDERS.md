# Screenshot placeholders

Capture these for the report or viva. Use a consistent window size and remove sensitive data before saving.

1. `ui-login.png` - DevPlane UI login.
2. `ui-catalog.png` - service catalog and environment actions.
3. `deployment-history.png` - deployment status and rollback entry.
4. `ops-registry.png` - ops tools with `source: kubernetes`.
5. `admin-audit.png` - admin metrics and immutable audit trail.
6. `jenkins-pipeline.png` - green Jenkins pipeline.
7. `docker-ps.png` - `docker compose ps`.
8. `k8s-pods.png` - `kubectl -n devplane get pods,pvc,hpa,ingress`.
9. `grafana.png` - DevPlane Grafana dashboard.
10. `loki-logs.png` - Loki query for `devplane-api`.
11. `argocd.png` - Argo CD Application synced.
12. `sonar.png` - SonarQube project overview.

Suggested commands for the cluster capture:

```powershell
kubectl -n devplane get pods,pvc,svc,hpa,ingress
kubectl -n devplane rollout status deploy/devplane-api
```

Store images in this directory and reference them from the technical report.
