"""Polls pending environments/deployments and expires TTL environments.

This is the multi-container demo worker. In production the same responsibilities
would be handled by Celery/RQ/Arq or a Kubernetes CronJob backed by Redis.
"""

import time

from app.core.logging import configure_logging, get_logger
from app.db.session import get_session
from app.models.deployment import Deployment
from app.models.environment import Environment
from app.services.environments import EnvironmentService
from app.services.metrics_refresh import refresh_business_metrics
from app.workers.provisioning import simulate_deployment, simulate_environment_provision

configure_logging()
logger = get_logger("devplane.worker.loop")


def loop() -> None:
    logger.info("worker_started")
    while True:
        db = get_session()
        try:
            pending_envs = db.query(Environment).filter(Environment.status == "provisioning").all()
            pending_deps = db.query(Deployment).filter(Deployment.status == "running").all()
            env_ids = [e.id for e in pending_envs]
            dep_ids = [d.id for d in pending_deps]
            reaped = EnvironmentService(db).reap_expired(actor="system:ttl-reaper")
            refresh_business_metrics(db)
            if reaped:
                logger.info("environments_expired", count=reaped)
        except Exception:
            logger.exception("worker_poll_failed")
            env_ids, dep_ids = [], []
        finally:
            db.close()

        for env_id in env_ids:
            simulate_environment_provision(env_id)
        for dep_id in dep_ids:
            simulate_deployment(dep_id)
        time.sleep(5)


if __name__ == "__main__":
    loop()
