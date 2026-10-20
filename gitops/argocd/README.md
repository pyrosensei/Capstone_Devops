# GitOps with Argo CD

1. Install Argo CD in the cluster:

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

2. Point `application.yaml` `repoURL` at your Git remote.
3. Apply the Application CR: `kubectl apply -f gitops/argocd/application.yaml`.
4. Push a change to `kubernetes/` on `main`. Argo CD detects drift and syncs.

Flow: Developer → GitHub (`main`) → Argo CD reconcile → Kubernetes → DevPlane users.

Credentials: retrieve the initial admin password with:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

Do not commit that password.
