from fastapi.testclient import TestClient


def test_ops_stubs(client: TestClient, auth_headers: dict[str, str]):
    pods = client.get("/api/v1/ops/pods", headers=auth_headers)
    assert pods.status_code == 200
    assert "pods" in pods.json()

    status = client.get("/api/v1/ops/deployment-status", headers=auth_headers)
    assert status.status_code == 200

    tf = client.get("/api/v1/ops/terraform-plan-status", headers=auth_headers)
    assert tf.status_code == 200
    assert tf.json()["status"] == "planned"

    jk = client.get("/api/v1/ops/jenkins-job-status", headers=auth_headers)
    assert jk.status_code == 200
    assert "job" in jk.json()
