from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("devplane.ops")


def _k8s_client():
    try:
        from kubernetes import client, config

        settings = get_settings()
        if settings.kubeconfig:
            config.load_kube_config(config_file=settings.kubeconfig)
        else:
            try:
                config.load_incluster_config()
            except Exception:
                config.load_kube_config()
        return client
    except Exception as exc:  # pragma: no cover - cluster optional in unit tests
        logger.warning("k8s_unavailable", error=str(exc))
        return None


class OpsRegistry:
    """Abstracts common platform operations behind a stable REST contract.

    Each tool uses the real integration when available (Kubernetes Python
    client, Jenkins API, Terraform plan artifact) and returns an honest ``stub``
    payload otherwise, so the control plane remains demoable on a laptop.
    """

    tools: dict[str, dict[str, Any]] = {
        "get_pods": {
            "path": "/api/v1/ops/pods",
            "description": "List pods in a namespace via the Kubernetes API.",
            "requires": "kubeconfig or in-cluster ServiceAccount",
        },
        "get_logs": {
            "path": "/api/v1/ops/logs?pod=<name>",
            "description": "Tail container logs for a pod.",
            "requires": "kubeconfig or in-cluster ServiceAccount",
        },
        "deployment_status": {
            "path": "/api/v1/ops/deployment-status?name=<deployment>",
            "description": "Read replica readiness for a Kubernetes Deployment.",
            "requires": "kubeconfig or in-cluster ServiceAccount",
        },
        "terraform_plan_status": {
            "path": "/api/v1/ops/terraform-plan-status",
            "description": "Summarize the latest Terraform plan artifact.",
            "requires": "terraform/tfplan.json (optional)",
        },
        "jenkins_job_status": {
            "path": "/api/v1/ops/jenkins-job-status?job=<job>",
            "description": "Read the last Jenkins build result.",
            "requires": "JENKINS_USER and JENKINS_TOKEN",
        },
    }

    def list_tools(self) -> dict[str, Any]:
        return {"tools": [{"name": name, **meta} for name, meta in self.tools.items()]}

    def _guard(self, tool: str, fn: Callable[[], Any]) -> Any:
        try:
            return fn()
        except Exception as exc:
            logger.warning("ops_tool_failed", tool=tool, error=str(exc))
            return {"source": "error", "tool": tool, "error": str(exc)}

    def get_pods(self, namespace: str = "default") -> dict[str, Any]:
        def _run():
            k8s = _k8s_client()
            if k8s is None:
                return {
                    "source": "stub",
                    "namespace": namespace,
                    "pods": [
                        {"name": "devplane-api-0", "status": "Running", "restarts": 0},
                        {"name": "devplane-worker-0", "status": "Running", "restarts": 0},
                    ],
                }
            v1 = k8s.CoreV1Api()
            items = v1.list_namespaced_pod(namespace=namespace).items
            return {
                "source": "kubernetes",
                "namespace": namespace,
                "pods": [
                    {
                        "name": p.metadata.name,
                        "status": p.status.phase,
                        "restarts": sum(
                            (cs.restart_count or 0)
                            for cs in (p.status.container_statuses or [])
                        ),
                    }
                    for p in items
                ],
            }

        return self._guard("get_pods", _run)

    def get_logs(self, pod: str, namespace: str = "default", tail: int = 100) -> dict[str, Any]:
        def _run():
            k8s = _k8s_client()
            if k8s is None:
                return {
                    "source": "stub",
                    "pod": pod,
                    "logs": "INFO waiting for local cluster; using stub logs\nINFO control plane healthy",
                }
            v1 = k8s.CoreV1Api()
            logs = v1.read_namespaced_pod_log(name=pod, namespace=namespace, tail_lines=tail)
            return {"source": "kubernetes", "pod": pod, "logs": logs}

        return self._guard("get_logs", _run)

    def deployment_status(self, name: str, namespace: str = "default") -> dict[str, Any]:
        def _run():
            k8s = _k8s_client()
            if k8s is None:
                return {
                    "source": "stub",
                    "name": name,
                    "ready_replicas": 1,
                    "replicas": 1,
                    "status": "Available",
                }
            apps = k8s.AppsV1Api()
            dep = apps.read_namespaced_deployment(name=name, namespace=namespace)
            spec_replicas = dep.spec.replicas or 0
            ready = dep.status.ready_replicas or 0
            return {
                "source": "kubernetes",
                "name": name,
                "replicas": spec_replicas,
                "ready_replicas": ready,
                "status": "Available" if ready == spec_replicas else "Progressing",
            }

        return self._guard("deployment_status", _run)

    def terraform_plan_status(self) -> dict[str, Any]:
        def _run():
            settings = get_settings()
            plan_path = Path(settings.terraform_state_dir) / "tfplan.json"
            if plan_path.exists():
                data = json.loads(plan_path.read_text(encoding="utf-8"))
                changes = data.get("resource_changes", [])
                actions = [tuple(change.get("change", {}).get("actions", [])) for change in changes]
                return {
                    "source": "terraform",
                    "workspace": data.get("format_version", "unknown"),
                    "status": "planned",
                    "adds": sum(1 for action in actions if action == ("create",)),
                    "changes": sum(1 for action in actions if "update" in action),
                    "destroys": sum(1 for action in actions if "delete" in action),
                    "plan_file": str(plan_path),
                }
            return {
                "source": "stub",
                "workspace": "local-kind",
                "status": "planned",
                "adds": 6,
                "changes": 1,
                "destroys": 0,
                "note": "Run terraform -chdir=terraform plan -out=tfplan && "
                "terraform -chdir=terraform show -json tfplan > terraform/tfplan.json",
            }

        return self._guard("terraform_plan_status", _run)

    def jenkins_job_status(self, job: str = "devplane-ci") -> dict[str, Any]:
        settings = get_settings()
        if not settings.jenkins_user or not settings.jenkins_token:
            return {
                "source": "stub",
                "job": job,
                "url": settings.jenkins_url,
                "last_build": 42,
                "result": "SUCCESS",
                "note": "Set JENKINS_USER and JENKINS_TOKEN for live status",
            }

        def _run():
            import httpx

            url = f"{settings.jenkins_url.rstrip('/')}/job/{job}/lastBuild/api/json"
            auth = (settings.jenkins_user, settings.jenkins_token)
            resp = httpx.get(url, auth=auth, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            return {
                "source": "jenkins",
                "job": job,
                "number": data.get("number"),
                "result": data.get("result"),
                "building": data.get("building"),
            }

        return self._guard("jenkins_job_status", _run)
