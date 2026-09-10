from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.source import Source
from app.models.think_tank import OrganizationTypeEnum, ThinkTank
from app.schemas.institution import ThinkTankCreate, ThinkTankUpdate


def normalize_url(url: object | None) -> str | None:
    """将 Pydantic URL 对象规范化为字符串。"""
    if url is None:
        return None
    return str(url)


class ThinkTankService:
    async def get_by_id(self, db: AsyncSession, think_tank_id: int, *, load_sources: bool = False) -> ThinkTank:
        statement = select(ThinkTank).where(ThinkTank.id == think_tank_id)
        if load_sources:
            statement = statement.options(selectinload(ThinkTank.sources))

        result = await db.execute(statement)
        think_tank = result.scalar_one_or_none()

        if think_tank is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="智库机构不存在。")
        return think_tank

    async def ensure_valid_parent(self, db: AsyncSession, *, parent_id: int | None, current_id: int | None = None) -> None:
        if parent_id is None:
            return
        if current_id is not None and parent_id == current_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="机构不能将自己设置为上级机构。")

        parent = await db.get(ThinkTank, parent_id)
        if parent is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="指定的上级机构不存在。")

    async def get_multi(
        self, db: AsyncSession, *, q: str | None = None, country: str | None = None,
        organization_type: OrganizationTypeEnum | None = None, parent_id: int | None = None,
        is_key: bool | None = None, is_active: bool | None = None, skip: int = 0, limit: int = 50
    ) -> list[ThinkTank]:
        statement = select(ThinkTank)
        if q:
            keyword = f"%{q.strip()}%"
            statement = statement.where(or_(
                ThinkTank.name.ilike(keyword),
                ThinkTank.name_en.ilike(keyword),
                ThinkTank.country.ilike(keyword)
            ))
        if country:
            statement = statement.where(ThinkTank.country == country.strip())
        if organization_type:
            statement = statement.where(ThinkTank.organization_type == organization_type)
        if parent_id is not None:
            statement = statement.where(ThinkTank.parent_id == parent_id)
        if is_key is not None:
            statement = statement.where(ThinkTank.is_key == is_key)
        if is_active is not None:
            statement = statement.where(ThinkTank.is_active == is_active)

        statement = statement.order_by(ThinkTank.is_key.desc(), ThinkTank.name.asc()).offset(skip).limit(limit)
        result = await db.execute(statement)
        return list(result.scalars().all())

    async def get_countries(self, db: AsyncSession) -> list[str]:
        statement = select(ThinkTank.country).distinct().order_by(ThinkTank.country.asc())
        result = await db.execute(statement)
        return list(result.scalars().all())

    async def get_without_active_sources(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 200,
    ) -> list[ThinkTank]:
        active_source_exists = (
            select(Source.id)
            .where(
                Source.think_tank_id == ThinkTank.id,
                Source.is_active.is_(True),
            )
            .exists()
        )

        statement = (
            select(ThinkTank)
            .where(
                ThinkTank.is_active.is_(True),
                ~active_source_exists,
            )
            .order_by(
                ThinkTank.is_key.desc(),
                ThinkTank.country.asc(),
                ThinkTank.name.asc(),
            )
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(statement)
        return list(result.scalars().all())

    async def get_statistics(self, db: AsyncSession) -> dict[str, int]:
        total_think_tanks = await db.scalar(select(func.count()).select_from(ThinkTank))
        active_think_tanks = await db.scalar(select(func.count()).select_from(ThinkTank).where(ThinkTank.is_active.is_(True)))
        key_think_tanks = await db.scalar(select(func.count()).select_from(ThinkTank).where(ThinkTank.is_key.is_(True)))
        total_sources = await db.scalar(select(func.count()).select_from(Source))
        active_sources = await db.scalar(select(func.count()).select_from(Source).where(Source.is_active.is_(True)))
        missing_active_sources = await db.scalar(
            select(func.count())
            .select_from(ThinkTank)
            .where(
                ThinkTank.is_active.is_(True),
                ~(
                    select(Source.id)
                    .where(
                        Source.think_tank_id == ThinkTank.id,
                        Source.is_active.is_(True),
                    )
                    .exists()
                ),
            )
        )

        return {
            "think_tanks": total_think_tanks or 0,
            "sources": total_sources or 0,
            "total_think_tanks": total_think_tanks or 0,
            "active_think_tanks": active_think_tanks or 0,
            "key_think_tanks": key_think_tanks or 0,
            "total_sources": total_sources or 0,
            "active_sources": active_sources or 0,
            "missing_active_sources": missing_active_sources or 0,
        }

    async def create(self, db: AsyncSession, payload: ThinkTankCreate) -> ThinkTank:
        await self.ensure_valid_parent(db, parent_id=payload.parent_id)

        think_tank = ThinkTank(
            key=payload.key.strip(),
            name=payload.name.strip(),
            name_en=payload.name_en.strip() if payload.name_en else None,
            country=payload.country.strip(),
            website=normalize_url(payload.website),
            description=payload.description.strip() if payload.description else None,
            organization_type=payload.organization_type,
            parent_id=payload.parent_id,
            is_key=payload.is_key,
            is_active=payload.is_active,
        )

        db.add(think_tank)
        try:
            await db.commit()
            await db.refresh(think_tank)
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="保存智库机构失败，可能存在重复数据。") from exc
        return think_tank

    async def update(self, db: AsyncSession, think_tank_id: int, payload: ThinkTankUpdate) -> ThinkTank:
        think_tank = await self.get_by_id(db, think_tank_id)
        update_data = payload.model_dump(exclude_unset=True)

        if "parent_id" in update_data:
            await self.ensure_valid_parent(db, parent_id=update_data["parent_id"], current_id=think_tank_id)

        for field_name, value in update_data.items():
            if field_name == "website":
                value = normalize_url(value)
            if isinstance(value, str):
                value = value.strip() or None
            setattr(think_tank, field_name, value)

        try:
            await db.commit()
            await db.refresh(think_tank)
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="更新智库机构失败。") from exc
        return think_tank

    async def delete(self, db: AsyncSession, think_tank_id: int) -> None:
        think_tank = await self.get_by_id(db, think_tank_id)
        await db.delete(think_tank)
        await db.commit()


think_tank_service = ThinkTankService()
