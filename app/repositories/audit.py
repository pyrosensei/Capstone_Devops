from typing import Sequence

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    def __init__(self, db: Session):
        super().__init__(db, AuditLog)

    def list_recent(
        self,
        limit: int = 100,
        action: str | None = None,
        resource_type: str | None = None,
    ) -> Sequence[AuditLog]:
        query = self.db.query(AuditLog)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        return query.order_by(AuditLog.id.desc()).limit(limit).all()

    def count(self) -> int:
        return self.db.query(AuditLog).count()

    def append(self, **kwargs) -> AuditLog:
        last = self.db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        seq = (last.sequence + 1) if last else 1
        entry = AuditLog(sequence=seq, **kwargs)
        return self.add(entry)
