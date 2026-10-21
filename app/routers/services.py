
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.environment import EnvironmentCreate, EnvironmentRead, EnvironmentUpdate
from app.schemas.flags import (
    FeatureFlagCreate,
    FeatureFlagRead,
    FeatureFlagUpdate,
    SecretRefCreate,
    SecretRefRead,
)
from app.schemas.service import ServiceCreate, ServiceRead, ServiceUpdate
from app.services.catalog import CatalogServiceLayer
from app.services.environments import EnvironmentService
from app.services.flags import FeatureFlagService, SecretReferenceService
from app.workers.provisioning import simulate_environment_provision

router = APIRouter(prefix="/api/v1/services", tags=["services"])


@router.get("", response_model=list[ServiceRead])
def list_services(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return CatalogServiceLayer(db).list()


@router.post("", response_model=ServiceRead, status_code=201)
def create_service(
    payload: ServiceCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ip = request.client.host if request.client else ""
    return CatalogServiceLayer(db).create(payload, user, ip)


@router.get("/{service_id}", response_model=ServiceRead)
def get_service(service_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return CatalogServiceLayer(db).get(service_id)


@router.patch("/{service_id}", response_model=ServiceRead)
def update_service(
    service_id: int,
    payload: ServiceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ip = request.client.host if request.client else ""
    return CatalogServiceLayer(db).update(service_id, payload, user, ip)


@router.delete("/{service_id}", status_code=204)
def delete_service(
    service_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    CatalogServiceLayer(db).delete(service_id, user, request.client.host if request.client else "")


@router.get("/{service_id}/environments", response_model=list[EnvironmentRead])
def list_envs(service_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return EnvironmentService(db).list(service_id)


@router.post("/{service_id}/environments", response_model=EnvironmentRead, status_code=201)
def create_env(
    service_id: int,
    payload: EnvironmentCreate,
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    env = EnvironmentService(db).create(
        service_id, payload, user, request.client.host if request.client else ""
    )
    background.add_task(simulate_environment_provision, env.id)
    return env


@router.patch("/environments/{env_id}", response_model=EnvironmentRead)
def update_env(
    env_id: int,
    payload: EnvironmentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return EnvironmentService(db).update(
        env_id, payload, user, request.client.host if request.client else ""
    )


@router.post("/environments/{env_id}/terminate", response_model=EnvironmentRead)
def terminate_env(
    env_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return EnvironmentService(db).terminate(
        env_id, user, request.client.host if request.client else ""
    )


@router.get("/{service_id}/flags", response_model=list[FeatureFlagRead])
def list_flags(service_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return FeatureFlagService(db).list(service_id)


@router.post("/{service_id}/flags", response_model=FeatureFlagRead, status_code=201)
def create_flag(
    service_id: int,
    payload: FeatureFlagCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return FeatureFlagService(db).create(
        service_id, payload, user, request.client.host if request.client else ""
    )


@router.patch("/{service_id}/flags/{flag_id}", response_model=FeatureFlagRead)
def update_flag(
    service_id: int,
    flag_id: int,
    payload: FeatureFlagUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return FeatureFlagService(db).update(
        service_id,
        flag_id,
        payload,
        user,
        request.client.host if request.client else "",
    )


@router.delete("/{service_id}/flags/{flag_id}", status_code=204)
def delete_flag(
    service_id: int,
    flag_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    FeatureFlagService(db).delete(
        service_id, flag_id, user, request.client.host if request.client else ""
    )


@router.get("/{service_id}/secrets", response_model=list[SecretRefRead])
def list_secrets(service_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return SecretReferenceService(db).list(service_id)


@router.post("/{service_id}/secrets", response_model=SecretRefRead, status_code=201)
def create_secret_ref(
    service_id: int,
    payload: SecretRefCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return SecretReferenceService(db).create(
        service_id, payload, user, request.client.host if request.client else ""
    )


@router.delete("/{service_id}/secrets/{secret_id}", status_code=204)
def delete_secret_ref(
    service_id: int,
    secret_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    SecretReferenceService(db).delete(
        service_id, secret_id, user, request.client.host if request.client else ""
    )
