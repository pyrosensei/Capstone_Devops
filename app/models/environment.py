from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Environment(TimestampMixin, Base):
    __tablename__ = "environments"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    env_type: Mapped[str] = mapped_column(String(32))  # ephemeral/dev/staging/prod
    status: Mapped[str] = mapped_column(String(32), default="provisioning")
    ttl_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cluster_namespace: Mapped[str] = mapped_column(String(128), default="default")

    service = relationship("CatalogService", back_populates="environments")
    deployments = relationship(
        "Deployment", back_populates="environment", cascade="all, delete-orphan"
    )
