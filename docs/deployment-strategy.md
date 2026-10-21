# Deployment strategy

## Rolling update (default)

`kubernetes/base/deployment-api.yaml` uses a rolling update with `maxUnavailable: 0` and `maxSurge: 1`. With two API replicas, at least one pod remains ready during a normal rollout.

```powershell
kubectl -n devplane set image deploy/devplane-api api=devplane-api:local
kubectl -n devplane rollout status deploy/devplane-api
kubectl -n devplane rollout undo deploy/devplane-api
```

## Blue-green

The main Service selects `app=devplane-api, version=blue`. Two color-specific Services are also provided:

- `devplane-api-blue` selects `version=blue`.
- `devplane-api-green` selects `version=green`.

Switch live traffic to green:

```powershell
kubectl -n devplane patch svc devplane-api --type merge --patch-file kubernetes/blue-green/select-green.json
```

Roll back by switching the selector back to blue:

```powershell
kubectl -n devplane patch svc devplane-api --type merge --patch-file kubernetes/blue-green/select-blue.json
```

The base manifests ship the blue Deployment only. To demonstrate green, create a second Deployment with `version: green` (or copy and relabel the API Deployment), scale it up, verify it, and then move the Service selector. The in-app deployment record stores `strategy: blue-green` so the control plane shows which strategy was requested.

## Canary

The canary is a separate track so it cannot receive traffic through the primary Service:

- `kubernetes/overlays/canary/canary.yaml` defines a `devplane-api-canary` Deployment labeled `version: canary`, a matching Service, and a second Ingress.
- The canary Ingress uses `nginx.ingress.kubernetes.io/canary: "true"` and `canary-weight: "10"`.
- NGINX sends roughly 10% of matching traffic to the canary Service.

Build and apply:

```powershell
docker build -t devplane-api:canary .
kind load docker-image devplane-api:canary --name devplane-kind
kubectl apply -k kubernetes/overlays/canary
```

Inspect:

```powershell
kubectl -n devplane get deploy,svc,ingress | Select-String canary
kubectl -n devplane logs deploy/devplane-api-canary --tail=50
```

Remove the canary:

```powershell
kubectl delete -f kubernetes/overlays/canary/canary.yaml
```

## Strategy recorded by the control plane

Deployments accept `rolling`, `blue-green`, or `canary`. The control plane records the requested strategy, status, version, and rollback state. The cluster manifests separately define how traffic is actually routed. The demo does not claim that the API performs a real Kubernetes rollout.

## Rollback behavior in the API

`POST /api/v1/deployments/{id}/rollback` creates a new deployment record pointing at the previous successful version and marks it as a rollback. This gives the platform an auditable release history independent of `kubectl rollout undo`.
