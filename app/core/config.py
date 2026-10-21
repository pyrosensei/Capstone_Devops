from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DevPlane"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    secret_key: str = "change-me-to-a-long-random-string"
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    database_url: str = "sqlite:///./data/devplane.db"
    redis_url: str = "redis://localhost:6379/0"
    provisioning_delay_seconds: int = 3

    bootstrap_admin_email: str = "admin@devplane.local"
    bootstrap_admin_password: str = "admin123"
    bootstrap_dev_email: str = "dev@devplane.local"
    bootstrap_dev_password: str = "dev123"

    kubeconfig: str = ""
    jenkins_url: str = "http://localhost:8080"
    jenkins_user: str = ""
    jenkins_token: str = ""
    terraform_state_dir: str = "./terraform"

    log_level: str = "INFO"
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
