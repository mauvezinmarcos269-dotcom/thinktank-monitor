from typing import Literal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.core.content_kind import ReportContentKind
from app.core.status import NotificationEventType, ReportAIStatus, ReportReviewStatus
from app.models.report import Report
from app.models.report_review_event import ReportReviewEvent
from app.models.source import Source
from app.models.user import RoleEnum
from app.schemas.report import ReportCreate, ReportUpdate
from app.services.notification_service import notification_service
from app.utils.datetime import utc_now_naive

ReportDeliverableStatus = Literal["complete", "partial", "empty"]


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
    review_status: ReportReviewStatus | None = None,
    ai_status: ReportAIStatus | None = None,
    content_kind: ReportContentKind | None = None,
    deliverable_status: ReportDeliverableStatus | None = None,
    keyword: str | None = None,
    think_tank_id: int | None = None,
    source_id: int | None = None,
) -> list[Report]:
    conditions = build_report_filters(
        review_status=review_status,
        ai_status=ai_status,
        content_kind=content_kind,
        deliverable_status=deliverable_status,
        keyword=keyword,
        think_tank_id=think_tank_id,
        source_id=source_id,
    )
    statement = select(Report)

    if think_tank_id is not None:
        statement = statement.join(Source, Source.id == Report.source_id)

    if conditions:
        statement = statement.where(*conditions)

    result = await db.execute(
        statement.order_by(Report.id.desc()).offset(skip).limit(limit)
    )

    return list(result.scalars().all())


async def count_reports(
    db: AsyncSession,
    *,
    review_status: ReportReviewStatus | None = None,
    ai_status: ReportAIStatus | None = None,
    content_kind: ReportContentKind | None = None,
    deliverable_status: ReportDeliverableStatus | None = None,
    keyword: str | None = None,
    think_tank_id: int | None = None,
    source_id: int | None = None,
) -> int:
    conditions = build_report_filters(
        review_status=review_status,
        ai_status=ai_status,
        content_kind=content_kind,
        deliverable_status=deliverable_status,
        keyword=keyword,
        think_tank_id=think_tank_id,
        source_id=source_id,
    )
    statement = select(func.count()).select_from(Report)

    if think_tank_id is not None:
        statement = statement.join(Source, Source.id == Report.source_id)

    if conditions:
        statement = statement.where(*conditions)

    total = await db.scalar(statement)
    return total or 0


def build_report_filters(
    *,
    review_status: ReportReviewStatus | None = None,
    ai_status: ReportAIStatus | None = None,
    content_kind: ReportContentKind | None = None,
    deliverable_status: ReportDeliverableStatus | None = None,
    keyword: str | None = None,
    think_tank_id: int | None = None,
    source_id: int | None = None,
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []

    if review_status is not None:
        conditions.append(Report.review_status == review_status.value)

    if ai_status is not None:
        conditions.append(Report.ai_status == ai_status.value)

    if content_kind is not None:
        conditions.append(Report.content_kind == content_kind.value)

    if deliverable_status is not None:
        deliverable_conditions = [
            func.length(func.trim(func.coalesce(Report.summary, ""))) > 0,
            func.length(func.trim(func.coalesce(Report.commentary, ""))) > 0,
            func.length(func.trim(func.coalesce(Report.translation, ""))) > 0,
        ]
        all_deliverables_ready = and_(*deliverable_conditions)
        any_deliverable_ready = or_(*deliverable_conditions)

        if deliverable_status == "complete":
            conditions.append(all_deliverables_ready)
        elif deliverable_status == "partial":
            conditions.append(
                and_(any_deliverable_ready, ~all_deliverables_ready)
            )
        elif deliverable_status == "empty":
            conditions.append(~any_deliverable_ready)

    if source_id is not None:
        conditions.append(Report.source_id == source_id)

    if think_tank_id is not None:
        conditions.append(Source.think_tank_id == think_tank_id)

    normalized_keyword = keyword.strip() if keyword else ""
    if normalized_keyword:
        pattern = f"%{normalized_keyword}%"
        keyword_conditions: list[ColumnElement[bool]] = [
            Report.title.ilike(pattern),
            Report.url.ilike(pattern),
        ]

        if normalized_keyword.isdigit():
            keyword_conditions.append(
                Report.id == int(normalized_keyword)
            )

        conditions.append(
            or_(*keyword_conditions)
        )

    return conditions


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
    reviewer_id: int | None = None,
) -> Report | None:
    obj = await get_report(db, report_id)

    if obj is None:
        return None

    update_data = data.model_dump(exclude_unset=True)
    previous_review_status = obj.review_status
    previous_review_note = obj.review_note
    review_updated = any(
        key in update_data
        for key in {
            "review_status",
            "review_note",
        }
    )

    if "review_note" in update_data and update_data["review_note"] is not None:
        update_data["review_note"] = update_data["review_note"].strip() or None

    for key, value in update_data.items():
        setattr(obj, key, value)

    if review_updated:
        reviewed_at = utc_now_naive()
        obj.reviewed_at = reviewed_at

        if (
            obj.review_status != previous_review_status
            or obj.review_note != previous_review_note
        ):
            db.add(
                ReportReviewEvent(
                    report_id=obj.id,
                    review_status=obj.review_status,
                    review_note=obj.review_note,
                    reviewer_id=reviewer_id,
                    created_at=reviewed_at,
                )
            )

        if (
            obj.review_status == ReportReviewStatus.needs_rerun.value
            and obj.review_status != previous_review_status
        ):
            await notification_service.create_for_roles(
                db,
                roles={RoleEnum.admin},
                event_type=NotificationEventType.report_review_needs_rerun.value,
                title="报告需重跑",
                message=(
                    f"{obj.title}\n\n"
                    f"复核意见：{obj.review_note or '老师未填写具体意见'}"
                ),
                report_id=obj.id,
            )

    await db.commit()
    await db.refresh(obj)

    return obj


async def get_report_review_events(
    db: AsyncSession,
    report_id: int,
) -> list[ReportReviewEvent] | None:
    report = await get_report(db, report_id)

    if report is None:
        return None

    result = await db.execute(
        select(ReportReviewEvent)
        .options(selectinload(ReportReviewEvent.reviewer))
        .where(ReportReviewEvent.report_id == report_id)
        .order_by(ReportReviewEvent.created_at.desc(), ReportReviewEvent.id.desc())
    )

    return list(result.scalars().all())


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
