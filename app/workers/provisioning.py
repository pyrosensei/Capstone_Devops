import time

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_session
from app.metrics import DEPLOYMENTS_TOTAL
from app.models.deployment import Deployment
from app.models.environment import Environment
from app.services.metrics_refresh import refresh_business_metrics

logger = get_logger("devplane.worker")


def simulate_environment_provision(environment_id: int) -> None:
    """Demo provisioner: flips provisioning -> running after a short delay.

    Safe to call twice (API background task + worker poller) because the status
    guard makes the operation idempotent.
    """
    delay = get_settings().provisioning_delay_seconds
    time.sleep(delay)
    db = get_session()
    try:
        env = db.get(Environment, environment_id)
        if not env or env.status != "provisioning":
            return
        env.status = "running"
        db.add(env)
        db.commit()
        refresh_business_metrics(db)
        logger.info("environment_provisioned", environment_id=environment_id)
    except Exception:
        db.rollback()
        logger.exception("environment_provision_failed", environment_id=environment_id)
        env = db.get(Environment, environment_id)
        if env:
            env.status = "failed"
            db.commit()
    finally:
        db.close()


def simulate_deployment(deployment_id: int) -> None:
    delay = get_settings().provisioning_delay_seconds
    time.sleep(delay)
    db = get_session()
    try:
        dep = db.get(Deployment, deployment_id)
        if not dep or dep.status != "running":
            return
        mode = "rolled back" if dep.is_rollback else "applied"
        dep.status = "succeeded"
        dep.logs_snippet = (
            f"[simulated-worker] {mode} version {dep.version} via {dep.strategy}\n"
            f"[simulated-worker] health checks passed after {delay}s\n"
            "[simulated-worker] no cluster resources were mutated"
        )
        db.add(dep)
        db.commit()
        DEPLOYMENTS_TOTAL.labels(status="succeeded", strategy=dep.strategy).inc()
        logger.info("deployment_finished", deployment_id=deployment_id, version=dep.version)
    except Exception:
        db.rollback()
        logger.exception("deployment_failed", deployment_id=deployment_id)
        dep = db.get(Deployment, deployment_id)
        if dep:
            dep.status = "failed"
            db.commit()
            DEPLOYMENTS_TOTAL.labels(status="failed", strategy=dep.strategy).inc()
    finally:
        db.close()
