from datetime import datetime
from typing import Sequence

from sqlalchemy.orm import Session

from app.models.environment import Environment
from app.repositories.base import BaseRepository


class EnvironmentRepository(BaseRepository[Environment]):
    def __init__(self, db: Session):
        super().__init__(db, Environment)

    def list_for_service(self, service_id: int) -> Sequence[Environment]:
        return (
            self.db.query(Environment)
            .filter(Environment.service_id == service_id)
            .order_by(Environment.id.desc())
            .all()
        )

    def count_by_status(self, status: str) -> int:
        return self.db.query(Environment).filter(Environment.status == status).count()

    def get_by_name_for_service(self, service_id: int, name: str) -> Environment | None:
        return (
            self.db.query(Environment)
            .filter(Environment.service_id == service_id, Environment.name == name)
            .first()
        )

    def list_expired(self, now: datetime) -> Sequence[Environment]:
        return (
            self.db.query(Environment)
            .filter(
                Environment.expires_at.is_not(None),
                Environment.expires_at <= now,
                Environment.status != "terminated",
            )
            .all()
        )
