from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class SecretReference(TimestampMixin, Base):
    """Reference to a secret stored outside the DB (K8s Secret / vault path). Never stores values."""

    __tablename__ = "secret_references"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), index=True)
    environment_id: Mapped[int | None] = mapped_column(ForeignKey("environments.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(128))
    provider: Mapped[str] = mapped_column(String(64), default="kubernetes")
    ref_path: Mapped[str] = mapped_column(String(512))  # e.g. secret/devplane/db-password

    service = relationship("CatalogService", back_populates="secret_refs")
