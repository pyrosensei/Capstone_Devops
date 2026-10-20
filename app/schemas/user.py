from typing import Literal

from pydantic import Field

from app.schemas.common import InternalEmail, ORMModel


class UserCreate(ORMModel):
    email: InternalEmail
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    role: Literal["admin", "developer"] = "developer"


class UserLogin(ORMModel):
    email: InternalEmail
    password: str


class UserRead(ORMModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool


class Token(ORMModel):
    access_token: str
    token_type: str = "bearer"
