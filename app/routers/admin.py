from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.db.session import get_db
from app.models.user import User
from app.repositories.audit import AuditRepository
from app.repositories.deployments import DeploymentRepository
from app.repositories.environments import EnvironmentRepository
from app.repositories.flags import FeatureFlagRepository, SecretRefRepository
from app.repositories.services import ServiceRepository
from app.repositories.users import UserRepository
from app.schemas.audit import AuditRead
from app.schemas.deployment import DeploymentRead
from app.services.environments import EnvironmentService
from app.services.metrics_refresh import refresh_business_metrics

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/metrics")
def overview(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    services = ServiceRepository(db).count()
    users = UserRepository(db).count_active()
    refresh_business_metrics(db)
    env_stats = {
        status: EnvironmentRepository(db).count_by_status(status)
        for status in ("provisioning", "running", "failed", "terminated")
    }
    deployment_stats = {
        status: DeploymentRepository(db).count_by_status(status)
        for status in ("pending", "running", "succeeded", "failed", "rolled_back")
    }
    return {
        "services": services,
        "active_users": users,
        "environments": env_stats,
        "deployments": deployment_stats,
        "feature_flags": FeatureFlagRepository(db).count(),
        "secret_references": SecretRefRepository(db).count(),
        "audit_entries": AuditRepository(db).count(),
        "recent_deployments": len(DeploymentRepository(db).list_recent(10)),
    }


@router.get("/audit", response_model=List[AuditRead])
def audit_logs(
    limit: int = Query(100, ge=1, le=1000),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return AuditRepository(db).list_recent(
        limit=limit, action=action, resource_type=resource_type
    )


@router.get("/deployments", response_model=List[DeploymentRead])
def recent_deployments(
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return DeploymentRepository(db).list_recent(limit)


@router.post("/maintenance/expire-environments")
def expire_environments(db: Session = Depends(get_db), user: User = Depends(require_admin)):
    """Manually run the TTL reaper (the worker also runs it every 5 seconds)."""
    count = EnvironmentService(db).reap_expired(actor=f"admin:{user.email}")
    return {"expired": count}
