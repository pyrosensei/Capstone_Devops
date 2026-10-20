# Blue-green and canary

## Blue-green

- `devplane-api` pods carry label `version=blue` or `version=green`.
- Service `devplane-api` is the live pointer (selector `app=devplane-api`).
- Services `devplane-api-blue` and `devplane-api-green` always target a color.

Switch traffic:

```bash
kubectl -n devplane patch svc devplane-api -p "{\"spec\":{\"selector\":{\"app\":\"devplane-api\",\"version\":\"green\"}}}"
```

Rollback:

```bash
kubectl -n devplane rollout undo deploy/devplane-api
# or point the Service selector back to version=blue
```

## Canary

Apply `kubernetes/canary-patch.yaml`. NGINX Ingress `canary-weight: "10"` sends ~10% of HTTP traffic to the canary backend.

In-app, deployments record `strategy` (`rolling` | `blue-green` | `canary`) so the control plane tracks which approach was used even when the cluster uses rolling updates.

## Rolling update / scale demo

```bash
kubectl -n devplane scale deploy/devplane-api --replicas=3
kubectl -n devplane set image deploy/devplane-api api=devplane-api:local
kubectl -n devplane rollout status deploy/devplane-api
kubectl -n devplane rollout undo deploy/devplane-api
```
