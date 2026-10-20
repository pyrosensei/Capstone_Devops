"""End-to-end API smoke test for a running DevPlane instance.

Usage:
    conda run -n capstone_devops python scripts/smoke.py
    python scripts/smoke.py --base-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import sys
import time
import uuid

import httpx


def wait_for(fn, predicate, attempts: int = 20, delay: float = 0.5):
    last = None
    for _ in range(attempts):
        last = fn()
        if predicate(last):
            return last
        time.sleep(delay)
    return last


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--email", default="admin@devplane.local")
    parser.add_argument("--password", default="admin123")
    args = parser.parse_args()

    with httpx.Client(base_url=args.base_url, timeout=15.0) as client:
        health = client.get("/health")
        health.raise_for_status()
        print(f"health: {health.json()}")

        login = client.post(
            "/api/v1/auth/login",
            data={"username": args.email, "password": args.password},
        )
        login.raise_for_status()
        token = login.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        print(f"logged in as {args.email}")

        suffix = uuid.uuid4().hex[:6]
        service = client.post(
            "/api/v1/services",
            json={
                "name": f"smoke-{suffix}",
                "description": "created by scripts/smoke.py",
                "repo_url": f"https://github.com/example/smoke-{suffix}",
                "tech_stack": "FastAPI",
            },
        )
        service.raise_for_status()
        sid = service.json()["id"]
        print(f"service: #{sid} {service.json()['name']}")

        env = client.post(
            f"/api/v1/services/{sid}/environments",
            json={"name": "smoke-staging", "env_type": "staging", "ttl_minutes": 30},
        )
        env.raise_for_status()
        env_id = env.json()["id"]
        print(f"environment: #{env_id} {env.json()['status']}")

        running = wait_for(
            lambda: client.get(f"/api/v1/services/{sid}/environments").json()[0],
            lambda item: item["status"] == "running",
        )
        print(f"environment after worker: {running['status']}")

        first = client.post(
            f"/api/v1/environments/{env_id}/deployments",
            json={"version": "v1.0.0", "commit_sha": "smoke111", "strategy": "blue-green"},
        )
        first.raise_for_status()
        second = client.post(
            f"/api/v1/environments/{env_id}/deployments",
            json={"version": "v2.0.0", "commit_sha": "smoke222", "strategy": "canary"},
        )
        second.raise_for_status()
        print(f"deployments: #{first.json()['id']} and #{second.json()['id']}")

        wait_for(
            lambda: client.get(f"/api/v1/deployments/{second.json()['id']}").json(),
            lambda item: item["status"] == "succeeded",
        )
        rollback = client.post(f"/api/v1/deployments/{second.json()['id']}/rollback")
        rollback.raise_for_status()
        print(f"rollback: #{rollback.json()['id']} -> {rollback.json()['version']}")

        flag = client.post(
            f"/api/v1/services/{sid}/flags",
            json={"key": "smoke-flag", "enabled": True},
        )
        flag.raise_for_status()
        print(f"feature flag: {flag.json()['key']}={flag.json()['enabled']}")

        tools = client.get("/api/v1/ops/tools")
        tools.raise_for_status()
        print(f"ops tools: {[t['name'] for t in tools.json()['tools']]}")

        pods = client.get("/api/v1/ops/pods?namespace=devplane")
        pods.raise_for_status()
        print(f"pods source: {pods.json().get('source')}")

        admin = client.get("/api/v1/admin/metrics")
        admin.raise_for_status()
        print(f"admin metrics: {admin.json()}")

        metrics = client.get("/metrics")
        metrics.raise_for_status()
        assert "devplane_http_requests_total" in metrics.text
        print("metrics scrape: OK")
        print("\nSmoke test passed.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except httpx.HTTPError as exc:
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        sys.exit(1)
