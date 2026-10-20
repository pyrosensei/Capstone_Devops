from fastapi.testclient import TestClient


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
        "role": "developer",
    }
    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201
    second = client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


def test_protected_route_without_token(client: TestClient):
    res = client.get("/api/v1/services")
    assert res.status_code == 401
