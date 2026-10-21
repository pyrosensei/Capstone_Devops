import re
from datetime import datetime
from typing import Annotated, Generic, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict

T = TypeVar("T")

# Internal platforms frequently use reserved/internal domains (for example
# ``*.local`` or ``*.internal``) that public email validators reject. We keep a
# strict RFC-ish local/domain syntax but deliberately allow internal TLDs.
_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)


def validate_internal_email(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) > 254 or not _EMAIL_RE.match(normalized):
        raise ValueError("value is not a valid email address")
    return normalized


InternalEmail = Annotated[str, AfterValidator(validate_internal_email)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    detail: str


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int


class Health(BaseModel):
    status: str
    app: str
    env: str
    time: datetime
    redis: str | None = None
