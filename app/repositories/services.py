
from sqlalchemy.orm import Session

from app.models.service import CatalogService
from app.repositories.base import BaseRepository


class ServiceRepository(BaseRepository[CatalogService]):
    def __init__(self, db: Session):
        super().__init__(db, CatalogService)

    def get_by_name(self, name: str) -> CatalogService | None:
        return self.db.query(CatalogService).filter(CatalogService.name == name).first()

    def count(self) -> int:
        return self.db.query(CatalogService).count()
