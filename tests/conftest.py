import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_test_db = Path(tempfile.gettempdir()) / f"devplane_test_{os.getpid()}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db.as_posix()}"
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

_test_db.parent.mkdir(parents=True, exist_ok=True)
if _test_db.exists():
    _test_db.unlink()

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


def pytest_sessionfinish(session, exitstatus):
    from app.db.session import reset_engine

    reset_engine()
    try:
        _test_db.unlink()
    except FileNotFoundError:
        pass
