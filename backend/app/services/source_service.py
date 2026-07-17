from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source, SourceTypeEnum
from app.schemas.institution import SourceCreate, SourceUpdate


class SourceService:
    async def get_by_id(self, db: AsyncSession, source_id: int) -> Source:
        source = await db.get(Source, source_id)
        if source is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="来源不存在。")
        return source

    async def get_by_think_tank(
        self, db: AsyncSession, think_tank_id: int, source_type: SourceTypeEnum | None = None, is_active: bool | None = None
    ) -> list[Source]:
        statement = select(Source).where(Source.think_tank_id == think_tank_id)
        if source_type:
            statement = statement.where(Source.source_type == source_type)
        if is_active is not None:
            statement = statement.where(Source.is_active == is_active)

        statement = statement.order_by(Source.id.asc())
        result = await db.execute(statement)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, think_tank_id: int, payload: SourceCreate) -> Source:
        source = Source(
            think_tank_id=think_tank_id,
            source_type=payload.source_type,
            url=str(payload.url),
            crawl_frequency_minutes=payload.crawl_frequency_minutes,
            is_active=payload.is_active,
        )
        db.add(source)
        try:
            await db.commit()
            await db.refresh(source)
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该 URL 已被其他来源使用。") from exc
        return source

    async def update(self, db: AsyncSession, source_id: int, payload: SourceUpdate) -> Source:
        source = await self.get_by_id(db, source_id)
        update_data = payload.model_dump(exclude_unset=True)

        for field_name, value in update_data.items():
            if field_name == "url" and value is not None:
                value = str(value)
            setattr(source, field_name, value)

        try:
            await db.commit()
            await db.refresh(source)
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="更新来源失败，该 URL 可能已存在。") from exc
        return source

    async def delete(self, db: AsyncSession, source_id: int) -> None:
        source = await self.get_by_id(db, source_id)
        await db.delete(source)
        await db.commit()


source_service = SourceService()
