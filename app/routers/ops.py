from fastapi import APIRouter, Depends, Query

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.exceptions import ForbiddenError
from app.models.user import User
from app.services.ops import OpsRegistry

router = APIRouter(prefix="/api/v1/ops", tags=["ops-registry"])


def _authorize_namespace(namespace: str) -> str:
    allowed = get_settings().ops_allowed_namespace_list
    if namespace not in allowed:
        raise ForbiddenError(
            f"Namespace {namespace!r} is not allowed; "
            f"allowed namespaces: {', '.join(allowed) or '(none)'}"
        )
    return namespace


@router.get("/tools")
def list_tools(_: User = Depends(get_current_user)):
    return OpsRegistry().list_tools()


@router.get("/pods")
def get_pods(namespace: str = "default", _: User = Depends(get_current_user)):
    return OpsRegistry().get_pods(_authorize_namespace(namespace))


@router.get("/logs")
def get_logs(
    pod: str = Query(..., min_length=1),
    namespace: str = "default",
    tail: int = Query(100, ge=1, le=5000),
    _: User = Depends(get_current_user),
):
    return OpsRegistry().get_logs(pod, _authorize_namespace(namespace), tail)


@router.get("/deployment-status")
def deployment_status(
    name: str = "devplane-api",
    namespace: str = "default",
    _: User = Depends(get_current_user),
):
    return OpsRegistry().deployment_status(name, _authorize_namespace(namespace))


@router.get("/terraform-plan-status")
def terraform_plan_status(_: User = Depends(get_current_user)):
    return OpsRegistry().terraform_plan_status()


@router.get("/jenkins-job-status")
def jenkins_job_status(job: str = "devplane-ci", _: User = Depends(get_current_user)):
    return OpsRegistry().jenkins_job_status(job)
