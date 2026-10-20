from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.metrics import SERVICES_GAUGE
from app.models.service import CatalogService
from app.models.user import User
from app.repositories.services import ServiceRepository
from app.schemas.service import ServiceCreate, ServiceUpdate
from app.services import audit


class CatalogServiceLayer:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ServiceRepository(db)

    def list(self):
        return self.repo.list()

    def get(self, service_id: int) -> CatalogService:
        service = self.repo.get(service_id)
        if not service:
            raise NotFoundError("Service not found")
        return service

    def create(self, payload: ServiceCreate, owner: User, ip: str = "") -> CatalogService:
        if self.repo.get_by_name(payload.name):
            raise ConflictError(f"Service '{payload.name}' already exists")
        service = CatalogService(
            name=payload.name,
            description=payload.description,
            repo_url=str(payload.repo_url),
            tech_stack=payload.tech_stack,
            status=payload.status,
            owner_id=owner.id,
        )
        service = self.repo.add(service)
        SERVICES_GAUGE.set(self.repo.count())
        audit.record(
            self.db,
            actor=owner.email,
            action="create",
            resource_type="service",
            resource_id=service.id,
            details=service.name,
            ip_address=ip,
        )
        return service

    def update(self, service_id: int, payload: ServiceUpdate, actor: User, ip: str = "") -> CatalogService:
        service = self.get(service_id)
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            if key == "repo_url" and value is not None:
                value = str(value)
            setattr(service, key, value)
        service = self.repo.save(service)
        audit.record(
            self.db,
            actor=actor.email,
            action="update",
            resource_type="service",
            resource_id=service.id,
            ip_address=ip,
        )
        return service

    def delete(self, service_id: int, actor: User, ip: str = "") -> None:
        service = self.get(service_id)
        name = service.name
        self.repo.delete(service)
        SERVICES_GAUGE.set(self.repo.count())
        audit.record(
            self.db,
            actor=actor.email,
            action="delete",
            resource_type="service",
            resource_id=service_id,
            details=name,
            ip_address=ip,
        )
