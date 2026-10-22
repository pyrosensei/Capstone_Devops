# Argo CD sync evidence

Captured during the validation session (Windows 11, Docker Desktop 29.6.2,
kind cluster `devplane-kind`, Kubernetes v1.37.0, Argo CD v3.5.6 installed with
`scripts/argocd-up.ps1`).

## Application status

```console
$ kubectl -n argocd get applications -o wide
NAME       SYNC STATUS   HEALTH STATUS   REVISION                                   PROJECT
devplane   Synced        Healthy         cf44e80036c0a624e8dd8516ce2346a57c7ced7e   default
```

The revision is the commit of `https://github.com/pyrosensei/Capstone_Devops.git`
that the Application tracks. Argo CD clones the public repository anonymously.

## Resource tree synced into the `devplane` namespace

```console
$ kubectl -n argocd get application devplane -o yaml
...
    kind: Deployment
    name: devplane-api
    status: Synced
    message: deployment.apps/devplane-api serverside-applied
    kind: Deployment
    name: devplane-worker
    status: Synced
    message: deployment.apps/devplane-worker serverside-applied
    kind: Deployment
    name: devplane-postgres
    status: Synced
    message: deployment.apps/devplane-postgres serverside-applied
    kind: Deployment
    name: devplane-redis
    status: Synced
    message: deployment.apps/devplane-redis serverside-applied
    kind: PersistentVolumeClaim
    name: devplane-postgres-data
    status: Synced
    message: persistentvolumeclaim/devplane-postgres-data serverside-applied
    kind: HorizontalPodAutoscaler
    name: devplane-api
    status: Synced
    kind: PodDisruptionBudget
    name: devplane-api
    status: Synced
    kind: ConfigMap
    name: devplane-config
    status: Synced
    kind: Ingress
    name: devplane
    status: Synced
    kind: Service
    name: devplane-api / devplane-api-blue / devplane-api-green / devplane-postgres / devplane-redis
    status: Synced
    kind: Role / RoleBinding
    name: devplane-ops
    status: Synced
    kind: ServiceAccount
    name: devplane
    status: Synced
```

## Notes

- The `devplane-secrets` Secret is **not** managed by Argo CD. It is created by
  `scripts/kind-up.ps1` (or Terraform/Ansible) and holds the JWT key, the
  PostgreSQL password, the bootstrap passwords and the metrics token.
- The Application ignores `spec.replicas` of `devplane-api` and uses
  `RespectIgnoreDifferences=true`, because the HorizontalPodAutoscaler owns the
  replica count.
- Screenshot: `docs/screenshots/argocd-applications.png`.
