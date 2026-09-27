from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crawl_run import CrawlRun
from app.models.report import Report
from app.models.source import CrawlStatusEnum, Source, SourceTypeEnum
from app.models.think_tank import ThinkTank
from app.schemas.institution import (
    CrawlRunRead,
    SourceCrawlRunListResponse,
    SourceCreate,
    SourceHealthListResponse,
    SourceHealthRead,
    SourceHealthSummary,
    SourceUpdate,
)
from app.services.source_diagnosis_service import classify_source_diagnosis
from app.services.source_rollout_policy import get_source_rollout_policy


class SourceService:
    async def get_by_id(self, db: AsyncSession, source_id: int) -> Source:
        source = await db.get(Source, source_id)
        if source is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="来源不存在。")
        return source

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        source_type: SourceTypeEnum | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 200,
    ) -> list[Source]:
        statement = select(Source)

        if source_type:
            statement = statement.where(Source.source_type == source_type)

        if is_active is not None:
            statement = statement.where(Source.is_active == is_active)

        statement = statement.order_by(Source.id.asc()).offset(skip).limit(limit)
        result = await db.execute(statement)
        return list(result.scalars().all())

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
        think_tank = await db.get(ThinkTank, think_tank_id)
        if think_tank is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="智库机构不存在。")

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

    async def get_health(
        self,
        db: AsyncSession,
        *,
        is_active: bool | None = None,
        limit: int = 500,
    ) -> SourceHealthListResponse:
        report_stats = (
            select(
                Report.source_id.label("source_id"),
                func.count(Report.id).label("report_count"),
                func.max(Report.created_at).label("latest_report_created_at"),
            )
            .group_by(Report.source_id)
            .subquery()
        )

        statement = (
            select(
                Source,
                ThinkTank.key.label("think_tank_key"),
                ThinkTank.name.label("think_tank_name"),
                ThinkTank.country.label("think_tank_country"),
                ThinkTank.priority_tier.label("think_tank_priority_tier"),
                ThinkTank.region_focus.label("think_tank_region_focus"),
                ThinkTank.is_verified.label("think_tank_is_verified"),
                report_stats.c.report_count,
                report_stats.c.latest_report_created_at,
            )
            .join(ThinkTank, ThinkTank.id == Source.think_tank_id)
            .outerjoin(report_stats, report_stats.c.source_id == Source.id)
        )

        if is_active is not None:
            statement = statement.where(Source.is_active == is_active)

        statement = statement.order_by(
            Source.is_active.desc(),
            Source.last_crawl_status.asc(),
            Source.id.asc(),
        ).limit(limit)

        rows = (await db.execute(statement)).all()
        source_ids = [source.id for source, *_ in rows]
        recent_runs_by_source = await self._get_recent_crawl_runs_by_source(
            db,
            source_ids=source_ids,
            limit_per_source=3,
        )
        items: list[SourceHealthRead] = []

        for (
            source,
            think_tank_key,
            think_tank_name,
            think_tank_country,
            think_tank_priority_tier,
            think_tank_region_focus,
            think_tank_is_verified,
            report_count,
            latest_report_created_at,
        ) in rows:
            health_status, health_reason = self._derive_health(source)
            diagnosis = classify_source_diagnosis(
                crawl_status=source.last_crawl_status,
                error_text=source.last_error,
                saved_report_count=int(report_count or 0),
            )
            rollout_policy = get_source_rollout_policy(
                str(think_tank_key)
            )
            items.append(
                SourceHealthRead(
                    id=source.id,
                    think_tank_id=source.think_tank_id,
                    source_type=source.source_type,
                    url=source.url,
                    crawl_frequency_minutes=source.crawl_frequency_minutes,
                    is_active=source.is_active,
                    last_crawl_status=source.last_crawl_status,
                    last_crawled_at=source.last_crawled_at,
                    last_error=source.last_error,
                    created_at=source.created_at,
                    updated_at=source.updated_at,
                    think_tank_name=think_tank_name,
                    think_tank_key=think_tank_key,
                    think_tank_country=think_tank_country,
                    think_tank_priority_tier=think_tank_priority_tier,
                    think_tank_region_focus=think_tank_region_focus,
                    think_tank_is_verified=think_tank_is_verified,
                    latest_report_created_at=latest_report_created_at,
                    report_count=int(report_count or 0),
                    health_status=health_status,
                    health_reason=health_reason,
                    diagnosis_code=diagnosis.code,
                    diagnosis_label=diagnosis.label,
                    diagnosis_advice=diagnosis.advice,
                    rollout_stage=rollout_policy.rollout_stage,
                    document_policy=rollout_policy.document_policy,
                    can_run_pilot_crawl=rollout_policy.can_run_pilot_crawl,
                    rollout_advice=rollout_policy.advice,
                    recent_crawl_runs=recent_runs_by_source.get(source.id, []),
                )
            )

        summary = SourceHealthSummary(
            total_sources=len(items),
            active_sources=sum(1 for item in items if item.is_active),
            healthy_sources=sum(1 for item in items if item.health_status == "healthy"),
            warning_sources=sum(1 for item in items if item.health_status == "warning"),
            failed_sources=sum(1 for item in items if item.health_status == "failed"),
            never_crawled_sources=sum(1 for item in items if item.health_status == "never"),
            disabled_sources=sum(1 for item in items if item.health_status == "disabled"),
        )

        return SourceHealthListResponse(summary=summary, items=items)

    async def get_recent_crawl_runs(
        self,
        db: AsyncSession,
        *,
        source_id: int | None = None,
        limit: int = 20,
    ) -> SourceCrawlRunListResponse:
        statement = select(CrawlRun)

        if source_id is not None:
            statement = statement.where(CrawlRun.source_id == source_id)

        statement = statement.order_by(
            CrawlRun.created_at.desc(),
            CrawlRun.id.desc(),
        ).limit(limit)

        rows = (await db.execute(statement)).scalars().all()
        return SourceCrawlRunListResponse(
            items=[self._to_crawl_run_read(crawl_run) for crawl_run in rows]
        )

    def _derive_health(self, source: Source) -> tuple[str, str]:
        if not source.is_active:
            return "disabled", "来源已停用。"

        if source.last_crawl_status == CrawlStatusEnum.failed:
            return "failed", source.last_error or "最近一次抓取失败。"

        if source.last_crawl_status == CrawlStatusEnum.running:
            return "warning", "来源正在抓取中。"

        if source.last_crawl_status == CrawlStatusEnum.never or source.last_crawled_at is None:
            return "never", "该来源尚未完成抓取。"

        last_crawled_at = source.last_crawled_at
        if last_crawled_at.tzinfo is None:
            last_crawled_at = last_crawled_at.replace(tzinfo=UTC)

        stale_after = timedelta(minutes=max(source.crawl_frequency_minutes * 2, 60))
        if datetime.now(UTC) - last_crawled_at > stale_after:
            return "warning", "超过两个抓取周期未更新。"

        return "healthy", "最近抓取正常。"

    async def _get_recent_crawl_runs_by_source(
        self,
        db: AsyncSession,
        *,
        source_ids: list[int],
        limit_per_source: int,
    ) -> dict[int, list[CrawlRunRead]]:
        if not source_ids:
            return {}

        ranked_runs = (
            select(
                CrawlRun.id.label("crawl_run_id"),
                func.row_number()
                .over(
                    partition_by=CrawlRun.source_id,
                    order_by=(CrawlRun.created_at.desc(), CrawlRun.id.desc()),
                )
                .label("rank"),
            )
            .where(CrawlRun.source_id.in_(source_ids))
            .subquery()
        )

        statement = (
            select(CrawlRun)
            .join(ranked_runs, ranked_runs.c.crawl_run_id == CrawlRun.id)
            .where(ranked_runs.c.rank <= limit_per_source)
            .order_by(CrawlRun.source_id.asc(), CrawlRun.created_at.desc(), CrawlRun.id.desc())
        )

        rows = (await db.execute(statement)).scalars().all()
        runs_by_source: dict[int, list[CrawlRunRead]] = {}

        for crawl_run in rows:
            runs_by_source.setdefault(crawl_run.source_id, []).append(
                self._to_crawl_run_read(crawl_run)
            )

        return runs_by_source

    def _to_crawl_run_read(self, crawl_run: CrawlRun) -> CrawlRunRead:
        duration_seconds: int | None = None

        if crawl_run.started_at and crawl_run.finished_at:
            duration_seconds = max(
                int((crawl_run.finished_at - crawl_run.started_at).total_seconds()),
                0,
            )

        return CrawlRunRead(
            id=crawl_run.id,
            source_id=crawl_run.source_id,
            status=crawl_run.status,
            found_count=crawl_run.found_count or 0,
            saved_count=crawl_run.saved_count or 0,
            error=crawl_run.error,
            started_at=crawl_run.started_at,
            finished_at=crawl_run.finished_at,
            created_at=crawl_run.created_at,
            duration_seconds=duration_seconds,
        )


source_service = SourceService()
