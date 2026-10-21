import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_non_development_rejects_default_secret_key():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(
            app_env="production",
            secret_key="change-me-to-a-long-random-string",
        )


def test_non_development_rejects_short_secret_key():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(app_env="docker", secret_key="too-short")


def test_non_development_accepts_strong_secret_and_bootstrap_passwords():
    settings = Settings(
        app_env="production",
        secret_key="a7f4d2c9e1b8f6a3d5c0e9b7a4f2d8c6e1b9a7f5d3c2e0b8a6f4d2c9e1b7a5f3",
        bootstrap_admin_password="admin-strong-password",
        bootstrap_dev_password="developer-strong-password",
    )
    assert settings.app_env == "production"


def test_non_development_rejects_demo_bootstrap_passwords():
    with pytest.raises(ValidationError, match="BOOTSTRAP_ADMIN_PASSWORD"):
        Settings(
            app_env="production",
            demo_mode=False,
            secret_key="a7f4d2c9e1b8f6a3d5c0e9b7a4f2d8c6e1b9a7f5d3c2e0b8a6f4d2c9e1b7a5f3",
            bootstrap_admin_password="admin123",
            bootstrap_dev_password="developer-strong-password",
        )


def test_demo_mode_explicitly_allows_demo_bootstrap_passwords():
    settings = Settings(
        app_env="docker",
        demo_mode=True,
        secret_key="a7f4d2c9e1b8f6a3d5c0e9b7a4f2d8c6e1b9a7f5d3c2e0b8a6f4d2c9e1b7a5f3",
    )
    assert settings.demo_mode is True


def test_unsafe_jwt_algorithms_are_rejected_in_every_environment():
    with pytest.raises(ValidationError, match="ALGORITHM"):
        Settings(app_env="development", algorithm="none")
