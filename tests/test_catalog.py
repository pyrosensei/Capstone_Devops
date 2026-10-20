from fastapi.testclient import TestClient


def test_seed_service_listed(client: TestClient, auth_headers: dict[str, str]):
    res = client.get("/api/v1/services", headers=auth_headers)
    assert res.status_code == 200
    names = [s["name"] for s in res.json()]
    assert "payments-api" in names


def test_create_update_delete_service(client: TestClient, auth_headers: dict[str, str]):
    created = client.post(
        "/api/v1/services",
        headers=auth_headers,
        json={
            "name": "checkout-api",
            "description": "Checkout",
            "repo_url": "https://github.com/example/checkout",
            "tech_stack": "Go",
        },
    )
    assert created.status_code == 201
    sid = created.json()["id"]

    patched = client.patch(
        f"/api/v1/services/{sid}",
        headers=auth_headers,
        json={"status": "deprecated"},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "deprecated"

    deleted = client.delete(f"/api/v1/services/{sid}", headers=auth_headers)
    assert deleted.status_code == 204


def test_flags_and_secret_refs(client: TestClient, auth_headers: dict[str, str]):
    services = client.get("/api/v1/services", headers=auth_headers).json()
    sid = services[0]["id"]
    flag = client.post(
        f"/api/v1/services/{sid}/flags",
        headers=auth_headers,
        json={"key": "new-checkout", "enabled": True, "description": "demo"},
    )
    assert flag.status_code == 201
    secret = client.post(
        f"/api/v1/services/{sid}/secrets",
        headers=auth_headers,
        json={"name": "db-password", "provider": "kubernetes", "ref_path": "secret/devplane/db"},
    )
    assert secret.status_code == 201
    assert "password" not in secret.json()["ref_path"] or secret.json()["name"] == "db-password"
