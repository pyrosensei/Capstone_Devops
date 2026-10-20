# syntax=docker/dockerfile:1
# ---- build stage: compile wheels / install deps into an isolated prefix ----
FROM python:3.11-slim-bookworm AS builder
WORKDIR /build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# ---- runtime stage: minimal, non-root ----
FROM python:3.11-slim-bookworm AS runtime
LABEL org.opencontainers.image.title="DevPlane API" \
      org.opencontainers.image.description="Self-hosted Internal Developer Platform control plane" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP_HOME=/app

WORKDIR /app
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin devplane \
    && mkdir -p /app/data /app/logs \
    && chown -R 10001:10001 /app

COPY --from=builder /install /usr/local
COPY --chown=10001:10001 app ./app
COPY --chown=10001:10001 worker ./worker
COPY --chown=10001:10001 alembic ./alembic
COPY --chown=10001:10001 alembic.ini .
COPY --chown=10001:10001 scripts/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0555 /usr/local/bin/entrypoint.sh

USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live')" || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
