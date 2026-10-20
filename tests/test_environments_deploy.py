from fastapi.testclient import TestClient


def test_environment_provision_and_deploy(client: TestClient, auth_headers: dict[str, str]):
    services = client.get("/api/v1/services", headers=auth_headers).json()
    sid = services[0]["id"]
    env = client.post(
        f"/api/v1/services/{sid}/environments",
        headers=auth_headers,
        json={"name": "staging", "env_type": "staging", "ttl_minutes": 60},
    )
    assert env.status_code == 201
    body = env.json()
    assert body["status"] in {"provisioning", "running"}
    env_id = body["id"]

    dep = client.post(
        f"/api/v1/environments/{env_id}/deployments",
        headers=auth_headers,
        json={"version": "v1.0.0", "commit_sha": "deadbeef", "strategy": "canary"},
    )
    assert dep.status_code == 201
    assert dep.json()["strategy"] == "canary"

    listed = client.get(f"/api/v1/environments/{env_id}/deployments", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()) >= 1

    terminated = client.post(
        f"/api/v1/services/environments/{env_id}/terminate",
        headers=auth_headers,
    )
    assert terminated.status_code == 200
    assert terminated.json()["status"] == "terminated"


def test_admin_metrics_and_audit(client: TestClient, auth_headers: dict[str, str]):
    metrics = client.get("/api/v1/admin/metrics", headers=auth_headers)
    assert metrics.status_code == 200
    assert "services" in metrics.json()
    audit = client.get("/api/v1/admin/audit", headers=auth_headers)
    assert audit.status_code == 200
    assert isinstance(audit.json(), list)
