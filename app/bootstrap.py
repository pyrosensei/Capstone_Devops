from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import hash_password
from app.models.service import CatalogService
from app.models.user import User

logger = get_logger("devplane.bootstrap")


def seed(db: Session) -> None:
    settings = get_settings()
    admin = db.query(User).filter(User.email == settings.bootstrap_admin_email).first()
    if not admin:
        admin = User(
            email=settings.bootstrap_admin_email,
            full_name="Platform Admin",
            hashed_password=hash_password(settings.bootstrap_admin_password),
            role="admin",
        )
        db.add(admin)
        logger.info("seeded_admin", email=settings.bootstrap_admin_email)

    developer = db.query(User).filter(User.email == settings.bootstrap_dev_email).first()
    if not developer:
        developer = User(
            email=settings.bootstrap_dev_email,
            full_name="Sample Developer",
            hashed_password=hash_password(settings.bootstrap_dev_password),
            role="developer",
        )
        db.add(developer)

    db.flush()
    if not db.query(CatalogService).first() and admin:
        db.add(
            CatalogService(
                name="payments-api",
                description="Sample catalog service used in demos",
                repo_url="https://github.com/example/payments-api",
                tech_stack="FastAPI, PostgreSQL",
                status="active",
                owner_id=admin.id,
            )
        )
    db.commit()
