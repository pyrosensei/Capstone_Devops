from fastapi.testclient import TestClient


def test_health(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["app"] == "DevPlane"


def test_metrics_endpoint(client: TestClient):
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "devplane_http_requests_total" in res.text or res.text.startswith("#") or "python" in res.text.lower()


def test_ui_index(client: TestClient):
    res = client.get("/")
    assert res.status_code == 200
    assert "DevPlane" in res.text
