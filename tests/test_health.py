from fastapi.testclient import TestClient


def test_health(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["app"] == "DevPlane"


def test_metrics_endpoint_requires_token(client: TestClient):
    anonymous = client.get("/metrics")
    assert anonymous.status_code == 401
    assert anonymous.headers.get("www-authenticate") == "Bearer"

    wrong = client.get("/metrics", headers={"Authorization": "Bearer not-the-token"})
    assert wrong.status_code == 401


def test_metrics_endpoint_returns_payload_with_token(client: TestClient):
    res = client.get(
        "/metrics", headers={"Authorization": "Bearer test-metrics-token-value"}
    )
    assert res.status_code == 200
    assert "devplane_http_requests_total" in res.text


def test_ui_index(client: TestClient):
    res = client.get("/")
    assert res.status_code == 200
    assert "DevPlane" in res.text
