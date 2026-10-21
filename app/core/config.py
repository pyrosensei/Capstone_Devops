from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEVELOPMENT_ENVIRONMENTS = {"development", "dev", "local", "test", "testing"}
_SECRET_KEY_PLACEHOLDERS = {
    "change-me",
    "change-me-in-compose",
    "change-me-to-a-long-random-string",
    "change-me-via-sealed-secrets-or-sops",
}
_DEMO_PASSWORDS = {"admin123", "dev123", "password", "changeme", "change-me"}
_ALLOWED_JWT_ALGORITHMS = {"HS256", "HS384", "HS512"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DevPlane"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    secret_key: str = "change-me-to-a-long-random-string"
    access_token_expire_minutes: int = Field(default=60, gt=0, le=1440)
    algorithm: str = "HS256"
    demo_mode: bool = False

    database_url: str = "sqlite:///./data/devplane.db"
    redis_url: str = "redis://localhost:6379/0"
    provisioning_delay_seconds: int = 3

    bootstrap_admin_email: str = "admin@devplane.local"
    bootstrap_admin_password: str = "admin123"
    bootstrap_dev_email: str = "dev@devplane.local"
    bootstrap_dev_password: str = "dev123"

    kubeconfig: str = ""
    ops_allowed_namespaces: str = "default,devplane"
    jenkins_url: str = "http://localhost:8080"
    jenkins_user: str = ""
    jenkins_token: str = ""
    terraform_state_dir: str = "./terraform"

    log_level: str = "INFO"
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.algorithm not in _ALLOWED_JWT_ALGORITHMS:
            raise ValueError(
                f"ALGORITHM must be one of {sorted(_ALLOWED_JWT_ALGORITHMS)}; "
                f"got {self.algorithm!r}"
            )

        key = self.secret_key.strip()
        if not key:
            raise ValueError("SECRET_KEY must not be empty")

        env = self.app_env.strip().lower()
        if env in _DEVELOPMENT_ENVIRONMENTS:
            return self

        normalized = key.lower()
        if (
            normalized in _SECRET_KEY_PLACEHOLDERS
            or normalized.startswith(("change-me", "replace-me", "changeme"))
            or len(key) < 32
        ):
            raise ValueError(
                f"SECRET_KEY must be a unique value of at least 32 characters when "
                f"APP_ENV={self.app_env!r}. Generate one with: "
                'python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )

        if not self.demo_mode:
            for name, password in (
                ("BOOTSTRAP_ADMIN_PASSWORD", self.bootstrap_admin_password),
                ("BOOTSTRAP_DEV_PASSWORD", self.bootstrap_dev_password),
            ):
                normalized_password = password.strip().lower()
                if normalized_password in _DEMO_PASSWORDS or len(password) < 12:
                    raise ValueError(
                        f"{name} must be changed to a value of at least 12 characters "
                        f"when APP_ENV={self.app_env!r} and DEMO_MODE is false"
                    )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def ops_allowed_namespace_list(self) -> list[str]:
        return [
            item.strip()
            for item in self.ops_allowed_namespaces.split(",")
            if item.strip()
        ]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
