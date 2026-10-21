from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from app.core.config import get_settings
from app.db.base import Base
from app import models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        is_postgres = connection.dialect.name == "postgresql"
        if is_postgres:
            # Serialize concurrent API pod migrations during a rolling rollout.
            connection.execute(text("SELECT pg_advisory_lock(47110815)"))
        try:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
            if is_postgres:
                # SQLAlchemy 2.0 opens a transaction for the advisory lock; the
                # migration must be committed explicitly before releasing it.
                connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            if is_postgres:
                connection.execute(text("SELECT pg_advisory_unlock(47110815)"))


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
