from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.feature_flag import FeatureFlag
from app.models.secret_ref import SecretReference
from app.models.user import User
from app.repositories.flags import FeatureFlagRepository, SecretRefRepository
from app.repositories.services import ServiceRepository
from app.schemas.flags import FeatureFlagCreate, FeatureFlagUpdate, SecretRefCreate
from app.services import audit


class FeatureFlagService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = FeatureFlagRepository(db)
        self.services = ServiceRepository(db)

    def _ensure_service(self, service_id: int) -> None:
        if not self.services.get(service_id):
            raise NotFoundError("Service not found")

    def list(self, service_id: int):
        self._ensure_service(service_id)
        return self.repo.list_for_service(service_id)

    def get(self, service_id: int, flag_id: int) -> FeatureFlag:
        self._ensure_service(service_id)
        flag = self.repo.get_for_service(service_id, flag_id)
        if not flag:
            raise NotFoundError("Feature flag not found")
        return flag

    def create(
        self, service_id: int, payload: FeatureFlagCreate, actor: User, ip: str = ""
    ) -> FeatureFlag:
        self._ensure_service(service_id)
        flag = FeatureFlag(service_id=service_id, **payload.model_dump())
        flag = self.repo.add(flag)
        audit.record(
            self.db,
            actor=actor.email,
            action="create",
            resource_type="feature_flag",
            resource_id=flag.id,
            details=f"{flag.key} enabled={flag.enabled}",
            ip_address=ip,
        )
        return flag

    def update(
        self,
        service_id: int,
        flag_id: int,
        payload: FeatureFlagUpdate,
        actor: User,
        ip: str = "",
    ) -> FeatureFlag:
        flag = self.get(service_id, flag_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(flag, key, value)
        flag = self.repo.save(flag)
        audit.record(
            self.db,
            actor=actor.email,
            action="update",
            resource_type="feature_flag",
            resource_id=flag.id,
            details=f"{flag.key} enabled={flag.enabled}",
            ip_address=ip,
        )
        return flag

    def delete(self, service_id: int, flag_id: int, actor: User, ip: str = "") -> None:
        flag = self.get(service_id, flag_id)
        key = flag.key
        self.repo.delete(flag)
        audit.record(
            self.db,
            actor=actor.email,
            action="delete",
            resource_type="feature_flag",
            resource_id=flag_id,
            details=key,
            ip_address=ip,
        )


class SecretReferenceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SecretRefRepository(db)
        self.services = ServiceRepository(db)

    def _ensure_service(self, service_id: int) -> None:
        if not self.services.get(service_id):
            raise NotFoundError("Service not found")

    def list(self, service_id: int):
        self._ensure_service(service_id)
        return self.repo.list_for_service(service_id)

    def create(
        self, service_id: int, payload: SecretRefCreate, actor: User, ip: str = ""
    ) -> SecretReference:
        self._ensure_service(service_id)
        ref = SecretReference(service_id=service_id, **payload.model_dump())
        ref = self.repo.add(ref)
        audit.record(
            self.db,
            actor=actor.email,
            action="create",
            resource_type="secret_reference",
            resource_id=ref.id,
            details=f"{ref.name} -> {ref.provider}:{ref.ref_path}",
            ip_address=ip,
        )
        return ref

    def delete(self, service_id: int, secret_id: int, actor: User, ip: str = "") -> None:
        self._ensure_service(service_id)
        ref = self.repo.get_for_service(service_id, secret_id)
        if not ref:
            raise NotFoundError("Secret reference not found")
        name = ref.name
        self.repo.delete(ref)
        audit.record(
            self.db,
            actor=actor.email,
            action="delete",
            resource_type="secret_reference",
            resource_id=secret_id,
            details=name,
            ip_address=ip,
        )
