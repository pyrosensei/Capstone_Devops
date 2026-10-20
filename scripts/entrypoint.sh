#!/usr/bin/env sh
set -eu

# Optionally apply migrations before serving. SQLite demos can rely on the
# application's create_all bootstrap; Postgres deployments should set
# RUN_MIGRATIONS=1 so Alembic owns the schema.
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "[entrypoint] running alembic upgrade head"
  alembic upgrade head
fi

exec "$@"
