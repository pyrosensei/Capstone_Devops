
from pydantic import Field, HttpUrl

from app.schemas.common import ORMModel


class ServiceCreate(ORMModel):
    name: str = Field(min_length=2, max_length=128)
    description: str = ""
    repo_url: HttpUrl
    tech_stack: str = ""
    status: str = "active"


class ServiceUpdate(ORMModel):
    description: str | None = None
    repo_url: HttpUrl | None = None
    tech_stack: str | None = None
    status: str | None = None
    owner_id: int | None = None


class ServiceRead(ORMModel):
    id: int
    name: str
    description: str
    repo_url: str
    tech_stack: str
    status: str
    owner_id: int
