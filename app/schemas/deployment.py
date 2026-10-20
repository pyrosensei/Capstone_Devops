from typing import Literal, Optional

from pydantic import Field

from app.schemas.common import ORMModel


class DeploymentCreate(ORMModel):
    version: str = Field(min_length=1, max_length=128)
    commit_sha: str = Field(default="", max_length=64)
    is_rollback: bool = False
    strategy: Literal["rolling", "blue-green", "canary"] = "rolling"


class DeploymentRead(ORMModel):
    id: int
    environment_id: int
    version: str
    commit_sha: str
    status: str
    logs_snippet: str
    is_rollback: bool
    triggered_by: str
    strategy: str


class DeploymentUpdate(ORMModel):
    status: Optional[Literal["pending", "running", "succeeded", "failed", "rolled_back"]] = None
    logs_snippet: Optional[str] = None
