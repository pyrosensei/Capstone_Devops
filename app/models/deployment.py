from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Deployment(TimestampMixin, Base):
    __tablename__ = "deployments"

    id: Mapped[int] = mapped_column(primary_key=True)
    environment_id: Mapped[int] = mapped_column(ForeignKey("environments.id"), index=True)
    version: Mapped[str] = mapped_column(String(128))
    commit_sha: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    logs_snippet: Mapped[str] = mapped_column(Text, default="")
    is_rollback: Mapped[bool] = mapped_column(Boolean, default=False)
    triggered_by: Mapped[str] = mapped_column(String(255), default="")
    strategy: Mapped[str] = mapped_column(String(32), default="rolling")  # rolling/blue-green/canary

    environment = relationship("Environment", back_populates="deployments")
