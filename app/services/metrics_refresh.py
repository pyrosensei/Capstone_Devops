from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.metrics import ACTIVE_USERS, ENVIRONMENTS_GAUGE, SERVICES_GAUGE
from app.models.environment import Environment
from app.models.service import CatalogService
from app.models.user import User


def refresh_business_metrics(db: Session | None = None) -> None:
    """Recompute point-in-time gauges from the database.

    Gauges must be *set* from source-of-truth counts rather than incremented so
    restarts and retries cannot drift the exported values.
    """
    owns_session = db is None
    if owns_session:
        db = get_session()
    try:
        ACTIVE_USERS.set(
            db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
        )
        SERVICES_GAUGE.set(db.query(func.count(CatalogService.id)).scalar() or 0)
        rows = (
            db.query(Environment.status, func.count(Environment.id))
            .group_by(Environment.status)
            .all()
        )
        counts = {status: count for status, count in rows}
        for status in ("provisioning", "running", "failed", "terminated"):
            ENVIRONMENTS_GAUGE.labels(status=status).set(counts.get(status, 0))
    finally:
        if owns_session:
            db.close()
