from datetime import datetime

from app.schemas.common import ORMModel


class AuditRead(ORMModel):
    id: int
    actor: str
    action: str
    resource_type: str
    resource_id: str
    details: str
    ip_address: str
    sequence: int
    created_at: datetime
