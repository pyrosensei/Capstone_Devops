# GitOps with Argo CD

Argo CD is installed into the same kind cluster as DevPlane and continuously
reconciles `kubernetes/overlays/dev` from GitHub. The Application CR in
`application.yaml` points at the real repository, so a commit to `kubernetes/`
is applied to the cluster automatically.

## 1. Install Argo CD and apply the Application

```powershell
powershell -ExecutionPolicy Bypass -File scripts/argocd-up.ps1
```

```bash
./scripts/argocd-up.sh
```

The script is pinned to Argo CD `v3.5.6`, waits for the control plane, and
applies `gitops/argocd/application.yaml`.

## 2. Open the UI

```powershell
kubectl -n argocd port-forward svc/argocd-server 8090:80
```

Then open <http://127.0.0.1:8090> (TLS is terminated by Argo CD, so use
`https://127.0.0.1:8090`).

The initial admin password is generated on first start. Two supported ways to
get a usable password:

```bash
# one-time password printed by the controller
kubectl -n argocd exec deploy/argocd-server -- argocd admin initial-password
```

```bash
# or set a password of your choice (the Secret stores a bcrypt hash)
kubectl -n argocd exec deploy/argocd-server -- argocd account bcrypt --password '<password>'
kubectl -n argocd patch secret argocd-secret --type merge \
  -p "{\"stringData\":{\"admin.password\":\"<bcrypt-hash>\",\"admin.passwordMtime\":\"<rfc3339>\"}}"
kubectl -n argocd rollout restart deploy/argocd-server
```

Do not commit the password or the hash.

## 3. Repository and revision

- `repoURL` points at `https://github.com/pyrosensei/Capstone_Devops.git`
  (a public repository, so Argo CD clones it anonymously - no credentials
  required).
- `targetRevision` is the branch that carries the Kubernetes manifests. It is
  currently `fix/auth-hardening`; switch it to `main` once that branch is
  merged, and Argo CD will follow `main` from then on.

## 4. The Secret is not managed by Argo CD

`kubernetes/base/secret.yaml` is intentionally **not** part of the repository.
The Secret is created by `scripts/kind-up.ps1` / `scripts/kind-up.sh` (or by
Terraform/Ansible) and holds the JWT key, the PostgreSQL password, the
bootstrap passwords and the metrics token. Argo CD does not track it, so it
never prunes or overwrites it.

## 5. Health and drift

```powershell
kubectl -n argocd get applications
kubectl -n argocd describe application devplane
kubectl -n argocd annotate application devplane argocd.argoproj.io/refresh=hard --overwrite
```

The Application ignores `spec.replicas` on `devplane-api` because the
HorizontalPodAutoscaler owns the replica count, and it uses
`RespectIgnoreDifferences=true` so Argo CD does not fight the autoscaler.

Flow: Developer -> GitHub -> Argo CD reconcile -> Kubernetes -> DevPlane users.
