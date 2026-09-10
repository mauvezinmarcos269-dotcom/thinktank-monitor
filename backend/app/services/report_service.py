from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report
from app.schemas.report import ReportCreate, ReportUpdate


async def create_report(
    db: AsyncSession,
    data: ReportCreate,
) -> Report:
    obj = Report(**data.model_dump())

    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    return obj


async def get_reports(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[Report]:
    result = await db.execute(
        select(Report).order_by(Report.id.desc()).offset(skip).limit(limit)
    )

    return list(result.scalars().all())


async def count_reports(db: AsyncSession) -> int:
    total = await db.scalar(select(func.count()).select_from(Report))
    return total or 0


async def get_report(
    db: AsyncSession,
    report_id: int,
) -> Report | None:
    result = await db.execute(
        select(Report).where(Report.id == report_id)
    )

    return result.scalar_one_or_none()


async def update_report(
    db: AsyncSession,
    report_id: int,
    data: ReportUpdate,
) -> Report | None:
    obj = await get_report(db, report_id)

    if obj is None:
        return None

    update_data = data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(obj, key, value)

    await db.commit()
    await db.refresh(obj)

    return obj


async def delete_report(
    db: AsyncSession,
    report_id: int,
) -> Report | None:
    obj = await get_report(db, report_id)

    if obj is None:
        return None

    await db.delete(obj)
    await db.commit()

    return obj
