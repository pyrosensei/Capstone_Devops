from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import ORMModel

ENV_TYPES = {"ephemeral", "dev", "staging", "prod"}
ENV_STATUSES = {"provisioning", "running", "failed", "terminated"}


class EnvironmentCreate(ORMModel):
    name: str = Field(min_length=1, max_length=64)
    env_type: Literal["ephemeral", "dev", "staging", "prod"]
    ttl_minutes: int | None = Field(default=None, ge=1)
    cluster_namespace: str = Field(default="default", min_length=1, max_length=128)


class EnvironmentUpdate(ORMModel):
    status: Literal["provisioning", "running", "failed", "terminated"] | None = None
    ttl_minutes: int | None = Field(default=None, ge=1)
    cluster_namespace: str | None = Field(default=None, min_length=1, max_length=128)


class EnvironmentRead(ORMModel):
    id: int
    service_id: int
    name: str
    env_type: str
    status: str
    ttl_minutes: int | None
    expires_at: datetime | None
    cluster_namespace: str
