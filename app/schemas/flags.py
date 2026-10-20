from typing import Literal, Optional

from pydantic import Field

from app.schemas.common import ORMModel


class FeatureFlagCreate(ORMModel):
    key: str = Field(min_length=1, max_length=128)
    enabled: bool = False
    description: str = ""
    environment_id: Optional[int] = None


class FeatureFlagUpdate(ORMModel):
    enabled: Optional[bool] = None
    description: Optional[str] = None
    environment_id: Optional[int] = None


class FeatureFlagRead(ORMModel):
    id: int
    service_id: int
    environment_id: Optional[int]
    key: str
    enabled: bool
    description: str


class SecretRefCreate(ORMModel):
    name: str = Field(min_length=1, max_length=128)
    provider: Literal["kubernetes", "vault", "aws-secrets-manager", "azure-key-vault"] = "kubernetes"
    ref_path: str = Field(min_length=1, max_length=512)
    environment_id: Optional[int] = None


class SecretRefRead(ORMModel):
    id: int
    service_id: int
    environment_id: Optional[int]
    name: str
    provider: str
    ref_path: str
