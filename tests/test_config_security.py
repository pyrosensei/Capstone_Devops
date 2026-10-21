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


def test_non_development_accepts_strong_secret_key():
    settings = Settings(
        app_env="production",
        secret_key="a7f4d2c9e1b8f6a3d5c0e9b7a4f2d8c6e1b9a7f5d3c2e0b8a6f4d2c9e1b7a5f3",
    )
    assert settings.app_env == "production"
