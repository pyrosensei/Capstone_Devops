import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./data/test_devplane.db"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["PROVISIONING_DELAY_SECONDS"] = "0"
os.environ["BOOTSTRAP_ADMIN_EMAIL"] = "admin@devplane.local"
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "admin123"
os.environ["BOOTSTRAP_DEV_EMAIL"] = "dev@devplane.local"
os.environ["BOOTSTRAP_DEV_PASSWORD"] = "dev123"
# Keep ops-registry tests deterministic even when the host has a live kubeconfig.
os.environ["KUBECONFIG"] = str(Path(__file__).parent / "nonexistent-kubeconfig")

from app.core.config import get_settings

get_settings.cache_clear()

from app.db.base import Base
from app.db.session import get_engine, reset_engine

Path("data").mkdir(exist_ok=True)
db_file = Path("data/test_devplane.db")
if db_file.exists():
    db_file.unlink()

reset_engine()
engine = get_engine()
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_token(client: TestClient) -> str:
    res = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@devplane.local", "password": "admin123"},
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


@pytest.fixture
def auth_headers(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}
