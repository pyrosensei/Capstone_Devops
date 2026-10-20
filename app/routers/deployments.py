from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.deployment import DeploymentCreate, DeploymentRead, DeploymentUpdate
from app.services.deployments import DeploymentService
from app.workers.provisioning import simulate_deployment

router = APIRouter(prefix="/api/v1", tags=["deployments"])


@router.get("/environments/{env_id}/deployments", response_model=List[DeploymentRead])
def list_deployments(env_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return DeploymentService(db).list(env_id)


@router.post("/environments/{env_id}/deployments", response_model=DeploymentRead, status_code=201)
def trigger_deployment(
    env_id: int,
    payload: DeploymentCreate,
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dep = DeploymentService(db).trigger(
        env_id, payload, user, request.client.host if request.client else ""
    )
    background.add_task(simulate_deployment, dep.id)
    return dep


@router.get("/deployments/{deployment_id}", response_model=DeploymentRead)
def get_deployment(
    deployment_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    return DeploymentService(db).get(deployment_id)


@router.post(
    "/deployments/{deployment_id}/rollback",
    response_model=DeploymentRead,
    status_code=201,
)
def rollback_deployment(
    deployment_id: int,
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dep = DeploymentService(db).rollback(
        deployment_id, user, request.client.host if request.client else ""
    )
    background.add_task(simulate_deployment, dep.id)
    return dep


@router.patch("/deployments/{deployment_id}/status", response_model=DeploymentRead)
def update_deployment_status(
    deployment_id: int,
    payload: DeploymentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    return DeploymentService(db).update_status(
        deployment_id, payload, user, request.client.host if request.client else ""
    )
