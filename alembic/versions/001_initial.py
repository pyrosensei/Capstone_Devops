"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(128), unique=True, nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("repo_url", sa.String(512), nullable=False),
        sa.Column("tech_stack", sa.String(255)),
        sa.Column("status", sa.String(32)),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "environments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_id", sa.Integer(), sa.ForeignKey("services.id")),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("env_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32)),
        sa.Column("ttl_minutes", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cluster_namespace", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "deployments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("environment_id", sa.Integer(), sa.ForeignKey("environments.id")),
        sa.Column("version", sa.String(128), nullable=False),
        sa.Column("commit_sha", sa.String(64)),
        sa.Column("status", sa.String(32)),
        sa.Column("logs_snippet", sa.Text()),
        sa.Column("is_rollback", sa.Boolean()),
        sa.Column("triggered_by", sa.String(255)),
        sa.Column("strategy", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor", sa.String(255)),
        sa.Column("action", sa.String(64)),
        sa.Column("resource_type", sa.String(64)),
        sa.Column("resource_id", sa.String(64)),
        sa.Column("details", sa.Text()),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("sequence", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "feature_flags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_id", sa.Integer(), sa.ForeignKey("services.id")),
        sa.Column("environment_id", sa.Integer(), sa.ForeignKey("environments.id"), nullable=True),
        sa.Column("key", sa.String(128)),
        sa.Column("enabled", sa.Boolean()),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "secret_references",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_id", sa.Integer(), sa.ForeignKey("services.id")),
        sa.Column("environment_id", sa.Integer(), sa.ForeignKey("environments.id"), nullable=True),
        sa.Column("name", sa.String(128)),
        sa.Column("provider", sa.String(64)),
        sa.Column("ref_path", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("secret_references")
    op.drop_table("feature_flags")
    op.drop_table("audit_logs")
    op.drop_table("deployments")
    op.drop_table("environments")
    op.drop_table("services")
    op.drop_table("users")
