from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class CatalogService(TimestampMixin, Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    repo_url: Mapped[str] = mapped_column(String(512))
    tech_stack: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), default="active")
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    owner = relationship("User", back_populates="owned_services")
    environments = relationship(
        "Environment", back_populates="service", cascade="all, delete-orphan"
    )
    feature_flags = relationship(
        "FeatureFlag", back_populates="service", cascade="all, delete-orphan"
    )
    secret_refs = relationship(
        "SecretReference", back_populates="service", cascade="all, delete-orphan"
    )
