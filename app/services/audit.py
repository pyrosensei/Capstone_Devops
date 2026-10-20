from sqlalchemy.orm import Session

from app.repositories.audit import AuditRepository


def record(
    db: Session,
    *,
    actor: str,
    action: str,
    resource_type: str,
    resource_id: str = "",
    details: str = "",
    ip_address: str = "",
) -> None:
    AuditRepository(db).append(
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        details=details,
        ip_address=ip_address,
    )
