from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.status import CrawlRunStatus, ReportAIStatus
from app.models.crawl_candidate import CrawlCandidate
from app.models.crawl_run import CrawlRun
from app.models.notification import Notification
from app.models.report import Report
from app.models.source import CrawlStatusEnum, Source
from app.models.think_tank import ThinkTank
from app.schemas.dashboard import (
    DashboardCrawlCandidates,
    DashboardOverview,
    DashboardResponse,
    DashboardSourceFailure,
    DashboardSourceHealth,
)
from app.schemas.institution import CrawlCandidateCountRead
from app.services.crawl_candidate_service import (
    get_candidate_status_label,
    get_skip_reason_label,
)
from app.services.source_service import source_service


class DashboardService:
    async def get_dashboard(
        self,
        db: AsyncSession,
        *,
        user_id: int,
    ) -> DashboardResponse:
        source_health_response = await source_service.get_health(
            db,
            limit=500,
        )

        overview = DashboardOverview(
            think_tanks=await self._count(db, ThinkTank),
            sources=await self._count(db, Source),
            reports=await self._count(db, Report),
            pending_crawl_runs=await self._count_where(
                db,
                CrawlRun,
                CrawlRun.status == CrawlRunStatus.pending.value,
            ),
            running_crawl_runs=await self._count_where(
                db,
                CrawlRun,
                CrawlRun.status == CrawlRunStatus.running.value,
            ),
            pending_ai_reports=await self._count_where(
                db,
                Report,
                Report.ai_status.in_(
                    (ReportAIStatus.pending.value, ReportAIStatus.queued.value)
                ),
            ),
            running_ai_reports=await self._count_where(
                db,
                Report,
                Report.ai_status.in_(
                    (
                        ReportAIStatus.processing.value,
                        ReportAIStatus.finalize_queued.value,
                        ReportAIStatus.finalizing.value,
                    )
                ),
            ),
            failed_ai_reports=await self._count_where(
                db,
                Report,
                Report.ai_status == ReportAIStatus.failed.value,
            ),
            unread_notifications=await self._count_where(
                db,
                Notification,
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            ),
        )

        source_health = DashboardSourceHealth(
            total_sources=source_health_response.summary.total_sources,
            active_sources=source_health_response.summary.active_sources,
            healthy_sources=source_health_response.summary.healthy_sources,
            warning_sources=source_health_response.summary.warning_sources,
            failed_sources=source_health_response.summary.failed_sources,
            never_crawled_sources=(
                source_health_response.summary.never_crawled_sources
            ),
            disabled_sources=source_health_response.summary.disabled_sources,
            recent_failures=await self._get_recent_source_failures(db),
        )

        return DashboardResponse(
            overview=overview,
            source_health=source_health,
            crawl_candidates=await self._get_crawl_candidate_summary(db),
        )

    async def _get_recent_source_failures(
        self,
        db: AsyncSession,
        *,
        limit: int = 5,
    ) -> list[DashboardSourceFailure]:
        statement = (
            select(Source, ThinkTank.name)
            .join(ThinkTank, ThinkTank.id == Source.think_tank_id)
            .where(Source.last_crawl_status == CrawlStatusEnum.failed)
            .order_by(Source.last_crawled_at.desc().nullslast(), Source.id.desc())
            .limit(limit)
        )
        rows = (await db.execute(statement)).all()

        return [
            DashboardSourceFailure(
                source_id=source.id,
                think_tank_name=think_tank_name,
                url=source.url,
                last_error=source.last_error,
                last_crawled_at=source.last_crawled_at,
            )
            for source, think_tank_name in rows
        ]

    async def _get_crawl_candidate_summary(
        self,
        db: AsyncSession,
    ) -> DashboardCrawlCandidates:
        total = await db.scalar(select(func.count(CrawlCandidate.id)))
        status_rows = (
            await db.execute(
                select(CrawlCandidate.status, func.count(CrawlCandidate.id))
                .group_by(CrawlCandidate.status)
                .order_by(CrawlCandidate.status.asc())
            )
        ).all()
        reason_rows = (
            await db.execute(
                select(
                    CrawlCandidate.skip_reason_code,
                    CrawlCandidate.skip_reason_label,
                    func.count(CrawlCandidate.id),
                )
                .where(CrawlCandidate.skip_reason_code.is_not(None))
                .group_by(
                    CrawlCandidate.skip_reason_code,
                    CrawlCandidate.skip_reason_label,
                )
                .order_by(func.count(CrawlCandidate.id).desc())
                .limit(8)
            )
        ).all()

        return DashboardCrawlCandidates(
            total=int(total or 0),
            by_status=[
                CrawlCandidateCountRead(
                    code=status,
                    label=get_candidate_status_label(status),
                    count=int(count),
                )
                for status, count in status_rows
            ],
            by_skip_reason=[
                CrawlCandidateCountRead(
                    code=reason_code,
                    label=reason_label or get_skip_reason_label(reason_code),
                    count=int(count),
                )
                for reason_code, reason_label, count in reason_rows
            ],
        )

    async def _count(self, db: AsyncSession, model: type) -> int:
        value = await db.scalar(select(func.count(model.id)))
        return int(value or 0)

    async def _count_where(self, db: AsyncSession, model: type, *conditions) -> int:
        statement = select(func.count(model.id))

        for condition in conditions:
            statement = statement.where(condition)

        value = await db.scalar(statement)
        return int(value or 0)


dashboard_service = DashboardService()
