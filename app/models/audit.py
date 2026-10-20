from sqlalchemy import Integer, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AuditLog(TimestampMixin, Base):
    """Append-only audit trail.

    There is deliberately no update/delete API. SQLAlchemy events below also
    reject accidental mutation at the ORM layer so the trail is immutable even
    if a future contributor adds a careless endpoint.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(255), index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str] = mapped_column(String(64), default="")
    details: Mapped[str] = mapped_column(Text, default="")
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    sequence: Mapped[int] = mapped_column(Integer, default=0, index=True)


@event.listens_for(AuditLog, "before_update")
def _reject_audit_update(mapper, connection, target):  # noqa: ARG001
    raise ValueError("Audit logs are immutable and cannot be updated")


@event.listens_for(AuditLog, "before_delete")
def _reject_audit_delete(mapper, connection, target):  # noqa: ARG001
    raise ValueError("Audit logs are immutable and cannot be deleted")
