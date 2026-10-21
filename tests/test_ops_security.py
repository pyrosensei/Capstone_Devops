import uuid

from fastapi.testclient import TestClient


def _developer_headers(client: TestClient) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/login",
        data={"username": "dev@devplane.local", "password": "dev123"},
    )
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_registration_normalizes_email_and_rejects_bad_input(client: TestClient):
    email = f"Mixed.Case.{uuid.uuid4().hex[:6]}@DevPlane.Local"
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Mixed Case", "password": "secret1"},
    )
    assert res.status_code == 201, res.text
    assert res.json()["email"] == email.lower()

    login = client.post(
        "/api/v1/auth/login",
        data={"username": email.upper(), "password": "secret1"},
    )
    assert login.status_code == 200

    bad = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "full_name": "Nope", "password": "secret1"},
    )
    assert bad.status_code == 422
    bad_role = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"role.{uuid.uuid4().hex[:6]}@devplane.local",
            "full_name": "Role",
            "password": "secret1",
            "role": "superuser",
        },
    )
    assert bad_role.status_code == 422


def test_registration_cannot_self_assign_admin(client: TestClient):
    email = f"privilege.{uuid.uuid4().hex[:6]}@devplane.local"
    escalated = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Privilege Escalation",
            "password": "secret1",
            "role": "admin",
        },
    )
    assert escalated.status_code == 422

    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Privilege Escalation",
            "password": "secret1",
        },
    )
    assert registered.status_code == 201, registered.text
    assert registered.json()["role"] == "developer"

    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "secret1"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/api/v1/admin/audit", headers=headers).status_code == 403


def test_ops_namespace_is_allowlisted(client: TestClient, auth_headers: dict[str, str]):
    denied = client.get(
        "/api/v1/ops/pods?namespace=kube-system",
        headers=auth_headers,
    )
    assert denied.status_code == 403

    denied_logs = client.get(
        "/api/v1/ops/logs?pod=test&namespace=kube-system",
        headers=auth_headers,
    )
    assert denied_logs.status_code == 403


def test_developer_role_is_limited(client: TestClient):
    headers = _developer_headers(client)
    service = client.post(
        "/api/v1/services",
        headers=headers,
        json={
            "name": f"dev-owned-{uuid.uuid4().hex[:8]}",
            "repo_url": "https://github.com/example/dev-owned",
        },
    )
    assert service.status_code == 201

    assert client.get("/api/v1/admin/metrics", headers=headers).status_code == 403
    assert client.get("/api/v1/admin/audit", headers=headers).status_code == 403
    assert client.delete(
        f"/api/v1/services/{service.json()['id']}", headers=headers
    ).status_code == 403


def test_ops_registry_tools_and_stubs(client: TestClient, auth_headers: dict[str, str]):
    tools = client.get("/api/v1/ops/tools", headers=auth_headers)
    assert tools.status_code == 200
    names = {tool["name"] for tool in tools.json()["tools"]}
    assert {"get_pods", "get_logs", "deployment_status"}.issubset(names)

    logs = client.get("/api/v1/ops/logs?pod=devplane-api-0", headers=auth_headers)
    assert logs.status_code == 200
    assert logs.json()["pod"] == "devplane-api-0"

    status = client.get(
        "/api/v1/ops/deployment-status?name=devplane-api&namespace=devplane",
        headers=auth_headers,
    )
    assert status.status_code == 200
    assert "status" in status.json()


def test_request_id_and_platform_health(client: TestClient):
    res = client.get("/health/live")
    assert res.status_code == 200
    assert res.headers["X-Request-ID"]

    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"

    health = client.get("/health")
    body = health.json()
    assert body["database"] == "ok"
    assert body["version"]

    supplied = client.get("/health/live", headers={"X-Request-ID": "demo-request"})
    assert supplied.headers["X-Request-ID"] == "demo-request"


def test_metrics_export_contains_platform_series(
    client: TestClient, auth_headers: dict[str, str]
):
    client.get("/api/v1/services", headers=auth_headers)
    client.get("/api/v1/admin/metrics", headers=auth_headers)
    metrics = client.get("/metrics")
    text = metrics.text
    for series in (
        "devplane_http_requests_total",
        "devplane_http_request_duration_seconds",
        "devplane_services",
        "devplane_environments",
        "devplane_active_users",
    ):
        assert series in text
