"""Dataset CRUD operations."""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.crud.base import CRUDBase
from app.models.dataset import Dataset
from app.schemas.dataset import DatasetCreate, DatasetUpdate


class CRUDDataset(CRUDBase[Dataset, DatasetCreate, DatasetUpdate]):
    async def get_by_project(
        self, db: AsyncSession, *, project_id: int, skip: int = 0, limit: int = 100
    ) -> List[Dataset]:
        result = await db.execute(
            select(Dataset)
            .where(Dataset.project_id == project_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_name(
        self, db: AsyncSession, *, project_id: int, name: str
    ) -> Optional[Dataset]:
        result = await db.execute(
            select(Dataset)
            .where(Dataset.project_id == project_id)
            .where(Dataset.name == name)
        )
        return result.scalar_one_or_none()


dataset = CRUDDataset(Dataset)