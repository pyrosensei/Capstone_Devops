from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.metrics import DEPLOYMENTS_TOTAL
from app.models.deployment import Deployment
from app.models.user import User
from app.repositories.deployments import DeploymentRepository
from app.repositories.environments import EnvironmentRepository
from app.schemas.deployment import DeploymentCreate, DeploymentUpdate
from app.services import audit


class DeploymentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DeploymentRepository(db)
        self.envs = EnvironmentRepository(db)

    def list(self, environment_id: int):
        if not self.envs.get(environment_id):
            raise NotFoundError("Environment not found")
        return self.repo.list_for_environment(environment_id)

    def get(self, deployment_id: int) -> Deployment:
        dep = self.repo.get(deployment_id)
        if not dep:
            raise NotFoundError("Deployment not found")
        return dep

    def _ensure_deployable(self, environment_id: int):
        env = self.envs.get(environment_id)
        if not env:
            raise NotFoundError("Environment not found")
        if env.status == "terminated":
            raise ConflictError("Environment is terminated; provision a new environment")
        return env

    def trigger(
        self, environment_id: int, payload: DeploymentCreate, actor: User, ip: str = ""
    ) -> Deployment:
        env = self._ensure_deployable(environment_id)
        logs = (
            f"[control-plane] queued {payload.strategy} deploy of {payload.version}\n"
            f"[control-plane] target env={env.name} ns={env.cluster_namespace}"
        )
        dep = Deployment(
            environment_id=environment_id,
            version=payload.version,
            commit_sha=payload.commit_sha,
            status="running",
            logs_snippet=logs,
            is_rollback=False,
            triggered_by=actor.email,
            strategy=payload.strategy,
        )
        dep = self.repo.add(dep)
        DEPLOYMENTS_TOTAL.labels(status="running", strategy=payload.strategy).inc()
        audit.record(
            self.db,
            actor=actor.email,
            action="deploy",
            resource_type="deployment",
            resource_id=dep.id,
            details=f"{payload.version} strategy={payload.strategy}",
            ip_address=ip,
        )
        return dep

    def rollback(self, deployment_id: int, actor: User, ip: str = "") -> Deployment:
        """Create a new deployment that restores the previous successful version."""
        current = self.get(deployment_id)
        self._ensure_deployable(current.environment_id)
        previous = self.repo.previous_successful(current.environment_id, current.id)
        if not previous:
            raise ConflictError("No previous successful deployment to roll back to")

        dep = Deployment(
            environment_id=current.environment_id,
            version=previous.version,
            commit_sha=previous.commit_sha,
            status="running",
            logs_snippet=(
                f"[control-plane] rollback requested from deployment #{current.id} "
                f"({current.version})\n"
                f"[control-plane] restoring #{previous.id} ({previous.version})"
            ),
            is_rollback=True,
            triggered_by=actor.email,
            strategy="rolling",
        )
        dep = self.repo.add(dep)
        DEPLOYMENTS_TOTAL.labels(status="running", strategy="rolling").inc()
        audit.record(
            self.db,
            actor=actor.email,
            action="rollback",
            resource_type="deployment",
            resource_id=dep.id,
            details=f"from={current.version} to={previous.version}",
            ip_address=ip,
        )
        return dep

    def update_status(
        self,
        deployment_id: int,
        payload: DeploymentUpdate,
        actor: User,
        ip: str = "",
    ) -> Deployment:
        dep = self.get(deployment_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(dep, key, value)
        dep = self.repo.save(dep)
        audit.record(
            self.db,
            actor=actor.email,
            action="update_status",
            resource_type="deployment",
            resource_id=dep.id,
            details=f"status={dep.status}",
            ip_address=ip,
        )
        return dep
