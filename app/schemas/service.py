from typing import Optional

from pydantic import Field, HttpUrl

from app.schemas.common import ORMModel


class ServiceCreate(ORMModel):
    name: str = Field(min_length=2, max_length=128)
    description: str = ""
    repo_url: HttpUrl
    tech_stack: str = ""
    status: str = "active"


class ServiceUpdate(ORMModel):
    description: Optional[str] = None
    repo_url: Optional[HttpUrl] = None
    tech_stack: Optional[str] = None
    status: Optional[str] = None
    owner_id: Optional[int] = None


class ServiceRead(ORMModel):
    id: int
    name: str
    description: str
    repo_url: str
    tech_stack: str
    status: str
    owner_id: int
