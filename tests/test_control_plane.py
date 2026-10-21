import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.db.session import get_session
from app.models.environment import Environment


def _create_service(client: TestClient, headers: dict[str, str]) -> int:
    name = f"svc-{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/v1/services",
        headers=headers,
        json={
            "name": name,
            "description": "test service",
            "repo_url": f"https://github.com/example/{name}",
            "tech_stack": "FastAPI",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_environment_lifecycle_and_ttl_reaper(client: TestClient, auth_headers: dict[str, str]):
    sid = _create_service(client, auth_headers)
    created = client.post(
        f"/api/v1/services/{sid}/environments",
        headers=auth_headers,
        json={"name": "ephemeral-pr", "env_type": "ephemeral", "ttl_minutes": 5},
    )
    assert created.status_code == 201, created.text
    env = created.json()
    assert env["status"] in {"provisioning", "running"}
    assert env["expires_at"]

    duplicate = client.post(
        f"/api/v1/services/{sid}/environments",
        headers=auth_headers,
        json={"name": "ephemeral-pr", "env_type": "ephemeral"},
    )
    assert duplicate.status_code == 409

    # Force expiry, then run the same reaper the worker uses.
    db = get_session()
    try:
        row = db.get(Environment, env["id"])
        row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    reaped = client.post("/api/v1/admin/maintenance/expire-environments", headers=auth_headers)
    assert reaped.status_code == 200
    assert reaped.json()["expired"] >= 1
    envs = client.get(f"/api/v1/services/{sid}/environments", headers=auth_headers).json()
    assert envs[0]["status"] == "terminated"

    terminated_deploy = client.post(
        f"/api/v1/environments/{env['id']}/deployments",
        headers=auth_headers,
        json={"version": "v9", "strategy": "rolling"},
    )
    assert terminated_deploy.status_code == 409


def test_deployment_update_and_rollback(client: TestClient, auth_headers: dict[str, str]):
    sid = _create_service(client, auth_headers)
    env = client.post(
        f"/api/v1/services/{sid}/environments",
        headers=auth_headers,
        json={"name": "prod", "env_type": "prod"},
    ).json()

    first = client.post(
        f"/api/v1/environments/{env['id']}/deployments",
        headers=auth_headers,
        json={"version": "v1.0.0", "commit_sha": "aaa111", "strategy": "blue-green"},
    )
    assert first.status_code == 201
    first_id = first.json()["id"]

    second = client.post(
        f"/api/v1/environments/{env['id']}/deployments",
        headers=auth_headers,
        json={"version": "v2.0.0", "commit_sha": "bbb222", "strategy": "canary"},
    )
    assert second.status_code == 201

    rollback = client.post(
        f"/api/v1/deployments/{second.json()['id']}/rollback", headers=auth_headers
    )
    assert rollback.status_code == 201, rollback.text
    body = rollback.json()
    assert body["is_rollback"] is True
    assert body["version"] == "v1.0.0"

    # Admin can force a terminal status for demos/incident drills.
    status_update = client.patch(
        f"/api/v1/deployments/{first_id}/status",
        headers=auth_headers,
        json={"status": "failed", "logs_snippet": "simulated failure"},
    )
    assert status_update.status_code == 200
    assert status_update.json()["status"] == "failed"


def test_flags_and_secret_references_crud(client: TestClient, auth_headers: dict[str, str]):
    sid = _create_service(client, auth_headers)
    flag = client.post(
        f"/api/v1/services/{sid}/flags",
        headers=auth_headers,
        json={"key": "checkout-v2", "enabled": False},
    )
    assert flag.status_code == 201
    flag_id = flag.json()["id"]

    patched = client.patch(
        f"/api/v1/services/{sid}/flags/{flag_id}",
        headers=auth_headers,
        json={"enabled": True, "description": "enabled for demo"},
    )
    assert patched.status_code == 200
    assert patched.json()["enabled"] is True

    secret = client.post(
        f"/api/v1/services/{sid}/secrets",
        headers=auth_headers,
        json={"name": "db-password", "provider": "vault", "ref_path": "secret/devplane/db"},
    )
    assert secret.status_code == 201
    secret_id = secret.json()["id"]

    assert client.delete(
        f"/api/v1/services/{sid}/flags/{flag_id}", headers=auth_headers
    ).status_code == 204
    assert client.delete(
        f"/api/v1/services/{sid}/secrets/{secret_id}", headers=auth_headers
    ).status_code == 204
    assert client.get(f"/api/v1/services/{sid}/flags", headers=auth_headers).json() == []
    assert client.get(f"/api/v1/services/{sid}/secrets", headers=auth_headers).json() == []


def test_audit_trail_is_ordered_and_immutable(client: TestClient, auth_headers: dict[str, str]):
    sid = _create_service(client, auth_headers)
    client.post(
        f"/api/v1/services/{sid}/flags",
        headers=auth_headers,
        json={"key": "audit-check", "enabled": True},
    )
    entries = client.get("/api/v1/admin/audit?limit=50", headers=auth_headers).json()
    assert entries
    assert entries[0]["sequence"] >= 1
    assert any(e["resource_type"] == "feature_flag" for e in entries)

    from app.models.audit import AuditLog

    db = get_session()
    try:
        row = db.query(AuditLog).first()
        row.details = "tampered"
        try:
            db.commit()
            raise AssertionError("audit log update should be rejected")
        except ValueError:
            db.rollback()
    finally:
        db.close()


def test_admin_metrics_include_new_sections(client: TestClient, auth_headers: dict[str, str]):
    res = client.get("/api/v1/admin/metrics", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    for key in ("services", "environments", "deployments", "feature_flags", "audit_entries"):
        assert key in body
