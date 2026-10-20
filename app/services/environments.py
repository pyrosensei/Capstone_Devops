from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.environment import Environment
from app.models.user import User
from app.repositories.environments import EnvironmentRepository
from app.repositories.services import ServiceRepository
from app.schemas.environment import EnvironmentCreate, EnvironmentUpdate
from app.services import audit
from app.services.metrics_refresh import refresh_business_metrics


class EnvironmentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EnvironmentRepository(db)
        self.services = ServiceRepository(db)

    def list(self, service_id: int):
        if not self.services.get(service_id):
            raise NotFoundError("Service not found")
        return self.repo.list_for_service(service_id)

    def get(self, env_id: int) -> Environment:
        env = self.repo.get(env_id)
        if not env:
            raise NotFoundError("Environment not found")
        return env

    def create(
        self, service_id: int, payload: EnvironmentCreate, actor: User, ip: str = ""
    ) -> Environment:
        if not self.services.get(service_id):
            raise NotFoundError("Service not found")
        if self.repo.get_by_name_for_service(service_id, payload.name):
            raise ConflictError(f"Environment '{payload.name}' already exists for this service")
        expires = None
        if payload.ttl_minutes:
            expires = datetime.now(timezone.utc) + timedelta(minutes=payload.ttl_minutes)
        env = Environment(
            service_id=service_id,
            name=payload.name,
            env_type=payload.env_type,
            status="provisioning",
            ttl_minutes=payload.ttl_minutes,
            expires_at=expires,
            cluster_namespace=payload.cluster_namespace,
        )
        env = self.repo.add(env)
        refresh_business_metrics(self.db)
        audit.record(
            self.db,
            actor=actor.email,
            action="create",
            resource_type="environment",
            resource_id=env.id,
            details=f"{payload.name}/{payload.env_type}",
            ip_address=ip,
        )
        return env

    def update(
        self, env_id: int, payload: EnvironmentUpdate, actor: User, ip: str = ""
    ) -> Environment:
        env = self.get(env_id)
        data = payload.model_dump(exclude_unset=True)
        if "ttl_minutes" in data:
            ttl = data["ttl_minutes"]
            env.ttl_minutes = ttl
            env.expires_at = (
                datetime.now(timezone.utc) + timedelta(minutes=ttl) if ttl else None
            )
        for key, value in data.items():
            if key != "ttl_minutes":
                setattr(env, key, value)
        env = self.repo.save(env)
        refresh_business_metrics(self.db)
        audit.record(
            self.db,
            actor=actor.email,
            action="update",
            resource_type="environment",
            resource_id=env.id,
            ip_address=ip,
        )
        return env

    def terminate(self, env_id: int, actor: User, ip: str = "") -> Environment:
        env = self.get(env_id)
        env.status = "terminated"
        env = self.repo.save(env)
        refresh_business_metrics(self.db)
        audit.record(
            self.db,
            actor=actor.email,
            action="terminate",
            resource_type="environment",
            resource_id=env.id,
            ip_address=ip,
        )
        return env

    def reap_expired(self, actor: str = "system") -> int:
        """Terminate environments whose TTL has elapsed. Returns count reaped."""
        now = datetime.now(timezone.utc)
        expired = self.repo.list_expired(now)
        for env in expired:
            env.status = "terminated"
            self.db.add(env)
            audit.record(
                self.db,
                actor=actor,
                action="expire",
                resource_type="environment",
                resource_id=env.id,
                details=f"ttl_minutes={env.ttl_minutes}",
            )
        if expired:
            self.db.commit()
            refresh_business_metrics(self.db)
        return len(expired)
