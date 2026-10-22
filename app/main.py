import time
import uuid
from contextlib import asynccontextmanager
from hmac import compare_digest
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

# Import models so SQLAlchemy registers metadata
from app import (
    __version__,
    models,  # noqa: F401
)
from app.bootstrap import seed
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.base import Base
from app.db.session import get_engine, get_session
from app.metrics import REQUEST_COUNT, REQUEST_LATENCY, metrics_response
from app.routers import admin, auth, deployments, ops, services, ui
from app.services.metrics_refresh import refresh_business_metrics

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("devplane")


@asynccontextmanager
async def lifespan(_: FastAPI):
    engine = get_engine()
    # SQLite demos rely on create_all for zero-friction startup. PostgreSQL
    # deployments run ``alembic upgrade head`` in the entrypoint so concurrent
    # API replicas cannot race table creation.
    if settings.is_sqlite:
        Base.metadata.create_all(bind=engine)
    db = get_session()
    try:
        seed(db)
    finally:
        db.close()
    refresh_business_metrics()
    logger.info("startup_complete", env=settings.app_env, version=__version__)
    yield
    logger.info("shutdown_complete")


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description=(
        "Self-hosted Internal Developer Platform control plane: catalog, "
        "environments, deployments, ops registry, audit and admin metrics."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(auth.router)
app.include_router(services.router)
app.include_router(deployments.router)
app.include_router(ops.router)
app.include_router(admin.router)
app.include_router(ui.router)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    structlog.contextvars.bind_contextvars(request_id=request_id)
    start = time.perf_counter()
    path = request.url.path
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request_failed", method=request.method, path=path)
        raise
    finally:
        elapsed = time.perf_counter() - start
        if not path.startswith("/metrics"):
            route = request.scope.get("route")
            # Use the templated route path to avoid unbounded metric cardinality.
            metric_path = getattr(route, "path", None) or (
                path if request.url.path in {"", "/"} else "unmatched"
            )
            REQUEST_LATENCY.labels(request.method, metric_path).observe(elapsed)
        structlog.contextvars.clear_contextvars()

    if not path.startswith("/metrics"):
        REQUEST_COUNT.labels(request.method, metric_path, str(response.status_code)).inc()
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-ms"] = f"{elapsed * 1000:.1f}"
    return response


@app.get("/health", tags=["platform"])
def health():
    db_status = "ok"
    db = get_session()
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
    finally:
        db.close()

    redis_status = "unconfigured"
    client = None
    try:
        import redis

        client = redis.from_url(settings.redis_url, socket_connect_timeout=0.4)
        client.ping()
        redis_status = "ok"
    except Exception:
        redis_status = "unavailable"
    finally:
        if client is not None:
            client.close()

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "app": settings.app_name,
        "version": __version__,
        "env": settings.app_env,
        "database": db_status,
        "redis": redis_status,
    }


@app.get("/health/live", tags=["platform"])
def liveness():
    return {"status": "ok"}


@app.get("/health/ready", tags=["platform"])
def readiness():
    db = get_session()
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("readiness_check_failed")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "detail": "database unavailable"},
        )
    finally:
        db.close()
    return {"status": "ready"}


@app.get("/metrics", tags=["platform"])
def metrics(request: Request):
    """Prometheus scrape endpoint.

    The endpoint is fail-closed: it is disabled until a token is configured
    and every request must present that token as a bearer credential.
    """
    token = settings.resolved_metrics_token
    if not token:
        return JSONResponse(
            status_code=503,
            content={"detail": "metrics endpoint disabled; set METRICS_TOKEN"},
        )
    header = request.headers.get("authorization", "")
    provided = header[len("bearer ") :].strip() if header.lower().startswith("bearer ") else ""
    if not provided or not compare_digest(provided, token):
        return JSONResponse(
            status_code=401,
            content={"detail": "invalid or missing metrics token"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload, content_type = metrics_response()
    return Response(content=payload, media_type=content_type)
