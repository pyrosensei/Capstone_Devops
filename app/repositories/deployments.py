from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.deployment import Deployment
from app.repositories.base import BaseRepository


class DeploymentRepository(BaseRepository[Deployment]):
    def __init__(self, db: Session):
        super().__init__(db, Deployment)

    def list_for_environment(self, environment_id: int) -> Sequence[Deployment]:
        return (
            self.db.query(Deployment)
            .filter(Deployment.environment_id == environment_id)
            .order_by(Deployment.id.desc())
            .all()
        )

    def list_recent(self, limit: int = 20) -> Sequence[Deployment]:
        return self.db.query(Deployment).order_by(Deployment.id.desc()).limit(limit).all()

    def previous_successful(
        self, environment_id: int, before_id: int
    ) -> Deployment | None:
        return (
            self.db.query(Deployment)
            .filter(
                Deployment.environment_id == environment_id,
                Deployment.id < before_id,
                Deployment.status == "succeeded",
            )
            .order_by(Deployment.id.desc())
            .first()
        )

    def count_by_status(self, status: str) -> int:
        return self.db.query(Deployment).filter(Deployment.status == status).count()
