import uuid

from fastapi.testclient import TestClient

from app.db.session import get_session
from app.models.user import User


def _create_service(client: TestClient, headers: dict[str, str]) -> int:
    name = f"hardening-{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/v1/services",
        headers=headers,
        json={
            "name": name,
            "description": "hardening regression service",
            "repo_url": f"https://github.com/example/{name}",
            "tech_stack": "FastAPI",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _create_environment(
    client: TestClient, headers: dict[str, str], service_id: int
) -> dict:
    res = client.post(
        f"/api/v1/services/{service_id}/environments",
        headers=headers,
        json={"name": f"env-{uuid.uuid4().hex[:6]}", "env_type": "dev"},
    )
    assert res.status_code == 201, res.text
    return res.json()


def _developer_headers(client: TestClient) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/login",
        data={"username": "dev@devplane.local", "password": "dev123"},
    )
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_inactive_user_cannot_log_in(client: TestClient):
    email = f"inactive.{uuid.uuid4().hex[:6]}@devplane.local"
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Inactive User", "password": "secret1"},
    )
    assert registered.status_code == 201, registered.text

    db = get_session()
    try:
        user = db.query(User).filter(User.email == email).one()
        user.is_active = False
        db.commit()
    finally:
        db.close()

    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "secret1"},
    )
    assert login.status_code == 401


def test_feature_flag_environment_must_belong_to_service(
    client: TestClient, auth_headers: dict[str, str]
):
    service_a = _create_service(client, auth_headers)
    service_b = _create_service(client, auth_headers)
    env_a = _create_environment(client, auth_headers, service_a)

    foreign = client.post(
        f"/api/v1/services/{service_b}/flags",
        headers=auth_headers,
        json={
            "key": f"foreign-{uuid.uuid4().hex[:6]}",
            "environment_id": env_a["id"],
        },
    )
    assert foreign.status_code == 404

    missing = client.post(
        f"/api/v1/services/{service_b}/flags",
        headers=auth_headers,
        json={"key": f"missing-{uuid.uuid4().hex[:6]}", "environment_id": 999999},
    )
    assert missing.status_code == 404


def test_secret_reference_environment_must_belong_to_service(
    client: TestClient, auth_headers: dict[str, str]
):
    service_a = _create_service(client, auth_headers)
    service_b = _create_service(client, auth_headers)
    env_a = _create_environment(client, auth_headers, service_a)

    res = client.post(
        f"/api/v1/services/{service_b}/secrets",
        headers=auth_headers,
        json={
            "name": f"secret-{uuid.uuid4().hex[:6]}",
            "ref_path": "secret/data/demo",
            "environment_id": env_a["id"],
        },
    )
    assert res.status_code == 404


def test_duplicate_flag_in_same_scope_is_rejected(
    client: TestClient, auth_headers: dict[str, str]
):
    service_id = _create_service(client, auth_headers)
    key = f"duplicate-{uuid.uuid4().hex[:6]}"
    first = client.post(
        f"/api/v1/services/{service_id}/flags",
        headers=auth_headers,
        json={"key": key},
    )
    assert first.status_code == 201, first.text

    second = client.post(
        f"/api/v1/services/{service_id}/flags",
        headers=auth_headers,
        json={"key": key},
    )
    assert second.status_code == 409


def test_developer_cannot_override_environment_status(
    client: TestClient, auth_headers: dict[str, str]
):
    service_id = _create_service(client, auth_headers)
    env = _create_environment(client, auth_headers, service_id)
    developer = _developer_headers(client)

    denied = client.patch(
        f"/api/v1/services/environments/{env['id']}",
        headers=developer,
        json={"status": "running"},
    )
    assert denied.status_code == 403

    allowed = client.patch(
        f"/api/v1/services/environments/{env['id']}",
        headers=auth_headers,
        json={"status": "running"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["status"] == "running"


def test_deployment_declares_simulated_execution(
    client: TestClient, auth_headers: dict[str, str]
):
    service_id = _create_service(client, auth_headers)
    env = _create_environment(client, auth_headers, service_id)

    res = client.post(
        f"/api/v1/environments/{env['id']}/deployments",
        headers=auth_headers,
        json={"version": "v-simulated", "is_rollback": True},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["execution_mode"] == "simulated"
    assert body["is_rollback"] is False


def test_readiness_does_not_leak_database_errors(client: TestClient, monkeypatch):
    class BrokenSession:
        def execute(self, *_args, **_kwargs):
            raise RuntimeError("password=super-secret database detail")

        def close(self):
            pass

    monkeypatch.setattr("app.main.get_session", lambda: BrokenSession())

    res = client.get("/health/ready")
    assert res.status_code == 503
    assert res.json() == {
        "status": "not_ready",
        "detail": "database unavailable",
    }


def test_ops_stubs_do_not_fabricate_success(
    client: TestClient, auth_headers: dict[str, str]
):
    pods = client.get("/api/v1/ops/pods?namespace=devplane", headers=auth_headers).json()
    assert pods["source"] == "stub"
    assert pods["status"] == "unavailable"
    assert pods["pods"] == []

    terraform = client.get(
        "/api/v1/ops/terraform-plan-status", headers=auth_headers
    ).json()
    assert terraform["source"] == "stub"
    assert terraform["status"] == "unavailable"
    assert terraform["adds"] == 0

    jenkins = client.get(
        "/api/v1/ops/jenkins-job-status?job=devplane-ci", headers=auth_headers
    ).json()
    assert jenkins["source"] == "stub"
    assert jenkins["result"] == "UNAVAILABLE"
    assert jenkins["last_build"] is None
