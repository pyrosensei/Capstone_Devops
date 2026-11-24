"""End-to-end API smoke test for a running DevPlane instance.

Usage:
    conda run -n capstone_devops python scripts/smoke.py
    python scripts/smoke.py --base-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from pathlib import Path

import httpx


def metrics_token() -> str:
    """Bearer token for the protected /metrics endpoint.

    Read from the environment first, then from the local .env file that
    scripts/setup-secrets.ps1 (or .sh) maintains.
    """
    token = os.environ.get("METRICS_TOKEN", "").strip()
    if token:
        return token
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("METRICS_TOKEN="):
                return line.split("=", 1)[1].strip()
    return ""


def wait_for_status(fetch, expected: str) -> dict:
    for _ in range(20):
        record = fetch()
        if record["status"] == expected:
            return record
        time.sleep(0.5)
    raise RuntimeError(f"Record #{record['id']} stayed {record['status']}; expected {expected}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--email", default=os.getenv("DEVPLANE_SMOKE_EMAIL", "admin@devplane.local"))
    parser.add_argument(
        "--password",
        default=os.getenv("DEVPLANE_SMOKE_PASSWORD", "admin123"),
        help="Login password. For hosted runs, set DEVPLANE_SMOKE_PASSWORD in the environment.",
    )
    parser.add_argument("--require-redis", action="store_true", help="Require a healthy Redis connection")
    parser.add_argument("--skip-metrics", action="store_true", help="Skip the Prometheus scrape")
    args = parser.parse_args()

    with httpx.Client(base_url=args.base_url, timeout=15.0) as client:
        def get_json(path: str):
            return client.get(path).raise_for_status().json()

        for path in ("/", "/static/app.js", "/static/styles.css", "/health/ready"):
            client.get(path).raise_for_status()
        print("UI entry point, static assets and readiness: OK")
        health = get_json("/health")
        print(f"health: {health}")
        if args.require_redis and health["redis"] != "ok":
            raise RuntimeError(f"Redis health is {health['redis']}; expected ok")

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
            json={"name": "smoke-preview", "env_type": "ephemeral", "ttl_minutes": 30},
        )
        env.raise_for_status()
        env_id = env.json()["id"]
        print(f"environment: #{env_id} {env.json()['status']}")

        running = wait_for_status(
            lambda: get_json(f"/api/v1/services/{sid}/environments")[0], "running"
        )
        print(f"environment after provisioning: {running['status']}")

        first = client.post(
            f"/api/v1/environments/{env_id}/deployments",
            json={"version": "v1.0.0", "commit_sha": "smoke111", "strategy": "blue-green"},
        )
        first.raise_for_status()
        first_id = first.json()["id"]
        wait_for_status(lambda: get_json(f"/api/v1/deployments/{first_id}"), "succeeded")
        second = client.post(
            f"/api/v1/environments/{env_id}/deployments",
            json={"version": "v2.0.0", "commit_sha": "smoke222", "strategy": "canary"},
        )
        second.raise_for_status()
        second_id = second.json()["id"]
        wait_for_status(lambda: get_json(f"/api/v1/deployments/{second_id}"), "succeeded")
        print(f"simulated deployments succeeded: #{first_id} and #{second_id}")

        rollback = client.post(f"/api/v1/deployments/{second_id}/rollback").raise_for_status()
        rollback_id = rollback.json()["id"]
        restored = wait_for_status(
            lambda: get_json(f"/api/v1/deployments/{rollback_id}"), "succeeded"
        )
        if restored["version"] != first.json()["version"] or not restored["is_rollback"]:
            raise RuntimeError("Rollback did not restore the first deployment version")
        print(f"rollback succeeded: #{rollback_id} -> {restored['version']}")

        flag = client.post(
            f"/api/v1/services/{sid}/flags",
            json={"key": "smoke-flag", "enabled": True},
        )
        flag.raise_for_status()
        print(f"feature flag: {flag.json()['key']}={flag.json()['enabled']}")

        secret_path = "devplane/smoke-key"
        client.post(
            f"/api/v1/services/{sid}/secrets",
            json={"name": "smoke-key", "provider": "kubernetes", "ref_path": secret_path},
        ).raise_for_status()
        refs = get_json(f"/api/v1/services/{sid}/secrets")
        if not any(ref["ref_path"] == secret_path for ref in refs):
            raise RuntimeError("Secret reference is missing from the service")
        print("secret reference: OK")

        tools = client.get("/api/v1/ops/tools")
        tools.raise_for_status()
        print(f"ops tools: {[t['name'] for t in tools.json()['tools']]}")

        pods = client.get("/api/v1/ops/pods?namespace=devplane")
        pods.raise_for_status()
        print(f"pods source: {pods.json().get('source')}")

        admin = client.get("/api/v1/admin/metrics")
        admin.raise_for_status()
        print(f"admin metrics: {admin.json()}")

        audit = get_json("/api/v1/admin/audit?action=rollback&resource_type=deployment")
        if not any(str(entry["resource_id"]) == str(rollback_id) for entry in audit):
            raise RuntimeError("Rollback audit entry is missing")
        print("rollback audit entry: OK")

        token = "" if args.skip_metrics else metrics_token()
        if not token:
            print("metrics scrape: skipped")
        else:
            anonymous_request = client.build_request("GET", "/metrics")
            anonymous_request.headers.pop("Authorization", None)
            anonymous = client.send(anonymous_request)
            if anonymous.status_code != 401:
                raise RuntimeError(
                    f"Anonymous metrics scrape returned HTTP {anonymous.status_code}; expected HTTP 401"
                )
            metrics = client.get("/metrics", headers={"Authorization": f"Bearer {token}"})
            metrics.raise_for_status()
            if "devplane_http_requests_total" not in metrics.text:
                raise RuntimeError("Prometheus scrape is missing the HTTP request counter")
            print("metrics scrape: anonymous HTTP 401, authenticated HTTP 200")
        print("\nSmoke test passed.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (httpx.HTTPError, RuntimeError) as exc:
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        sys.exit(1)
