from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings


def test_login_and_me(client: TestClient, auth_headers: dict[str, str]):
    me = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me.status_code == 200
    assert me.json()["role"] == "admin"


def test_login_rejects_bad_password(client: TestClient):
    res = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@devplane.local", "password": "wrong"},
    )
    assert res.status_code == 401


def test_register_and_conflict(client: TestClient):
    payload = {
        "email": "new.dev@devplane.local",
        "full_name": "New Dev",
        "password": "secret1",
    }
    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201
    assert first.json()["role"] == "developer"
    second = client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


def test_protected_route_without_token(client: TestClient):
    res = client.get("/api/v1/services")
    assert res.status_code == 401


def test_hosted_signup_is_closed_and_login_has_no_demo_credentials(client, monkeypatch):
    production = Settings(
        app_env="production",
        demo_mode=False,
        secret_key="long-random-test-key-for-hosted-settings",
        bootstrap_admin_password="hosted-admin-test-password",
        bootstrap_dev_password="hosted-dev-test-password",
    )
    monkeypatch.setitem(client.app.dependency_overrides, get_settings, lambda: production)
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "visitor@example.com", "full_name": "Visitor", "password": "password123"},
    )
    assert response.status_code == 403

    page = client.get("/")
    assert page.status_code == 200
    for credential in ("admin@devplane.local", "admin123", "dev@devplane.local", "dev123"):
        assert credential not in page.text
    assert 'name="email" autocomplete="username" required' in page.text
    assert 'name="password" type="password" autocomplete="current-password" required' in page.text


def test_demo_login_keeps_sample_accounts(client, monkeypatch):
    demo = get_settings().model_copy(update={"demo_mode": True})
    monkeypatch.setitem(client.app.dependency_overrides, get_settings, lambda: demo)
    page = client.get("/")
    assert page.status_code == 200
    assert 'value="admin@devplane.local"' in page.text
    assert 'value="admin123"' in page.text
    assert "dev@devplane.local / dev123" in page.text
