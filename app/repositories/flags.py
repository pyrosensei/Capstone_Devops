from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.models.feature_flag import FeatureFlag
from app.models.secret_ref import SecretReference
from app.repositories.base import BaseRepository


class FeatureFlagRepository(BaseRepository[FeatureFlag]):
    def __init__(self, db: Session):
        super().__init__(db, FeatureFlag)

    def list_for_service(self, service_id: int) -> Sequence[FeatureFlag]:
        return self.db.query(FeatureFlag).filter(FeatureFlag.service_id == service_id).all()

    def get_for_service(self, service_id: int, flag_id: int) -> Optional[FeatureFlag]:
        return (
            self.db.query(FeatureFlag)
            .filter(FeatureFlag.service_id == service_id, FeatureFlag.id == flag_id)
            .first()
        )

    def count(self) -> int:
        return self.db.query(FeatureFlag).count()


class SecretRefRepository(BaseRepository[SecretReference]):
    def __init__(self, db: Session):
        super().__init__(db, SecretReference)

    def list_for_service(self, service_id: int) -> Sequence[SecretReference]:
        return (
            self.db.query(SecretReference)
            .filter(SecretReference.service_id == service_id)
            .all()
        )

    def get_for_service(
        self, service_id: int, secret_id: int
    ) -> Optional[SecretReference]:
        return (
            self.db.query(SecretReference)
            .filter(
                SecretReference.service_id == service_id,
                SecretReference.id == secret_id,
            )
            .first()
        )

    def count(self) -> int:
        return self.db.query(SecretReference).count()
