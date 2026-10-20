from datetime import datetime
from typing import Literal, Optional

from pydantic import Field

from app.schemas.common import ORMModel

ENV_TYPES = {"ephemeral", "dev", "staging", "prod"}
ENV_STATUSES = {"provisioning", "running", "failed", "terminated"}


class EnvironmentCreate(ORMModel):
    name: str = Field(min_length=1, max_length=64)
    env_type: Literal["ephemeral", "dev", "staging", "prod"]
    ttl_minutes: Optional[int] = Field(default=None, ge=1)
    cluster_namespace: str = Field(default="default", min_length=1, max_length=128)


class EnvironmentUpdate(ORMModel):
    status: Optional[Literal["provisioning", "running", "failed", "terminated"]] = None
    ttl_minutes: Optional[int] = Field(default=None, ge=1)
    cluster_namespace: Optional[str] = Field(default=None, min_length=1, max_length=128)


class EnvironmentRead(ORMModel):
    id: int
    service_id: int
    name: str
    env_type: str
    status: str
    ttl_minutes: Optional[int]
    expires_at: Optional[datetime]
    cluster_namespace: str
