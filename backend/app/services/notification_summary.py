from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.content_kind import get_content_kind_label
from app.core.status import ReportAIStatus
from app.models.crawl_candidate import CrawlCandidate
from app.models.report import Report
from app.models.source import CrawlStatusEnum, Source
from app.models.think_tank import ThinkTank
from app.services.crawl_candidate_service import get_candidate_status_label


@dataclass(frozen=True)
class DailySummary:
    title: str
    message: str
    metrics: dict[str, int]


async def count_where(db: AsyncSession, model: type, *conditions) -> int:
    statement = select(func.count(model.id))

    for condition in conditions:
        statement = statement.where(condition)

    value = await db.scalar(statement)
    return int(value or 0)


async def build_daily_summary(
    db: AsyncSession,
    *,
    since: datetime,
    lookback_hours: int,
) -> DailySummary:
    new_reports = await count_where(
        db,
        Report,
        Report.created_at >= since,
    )
    failed_sources = await count_where(
        db,
        Source,
        Source.last_crawl_status == CrawlStatusEnum.failed,
    )
    saved_candidates = await count_where(
        db,
        CrawlCandidate,
        CrawlCandidate.status == "saved",
        CrawlCandidate.created_at >= since,
    )
    skipped_candidates = await count_where(
        db,
        CrawlCandidate,
        CrawlCandidate.status == "skipped",
        CrawlCandidate.created_at >= since,
    )
    ai_completed_reports = await count_where(
        db,
        Report,
        Report.ai_status == ReportAIStatus.success.value,
        Report.ai_generated_at >= since,
    )
    ai_failed_reports = await count_where(
        db,
        Report,
        Report.ai_status == ReportAIStatus.failed.value,
        Report.updated_at >= since,
    )
    candidate_rows = (
        await db.execute(
            select(CrawlCandidate.status, func.count(CrawlCandidate.id))
            .where(CrawlCandidate.created_at >= since)
            .group_by(CrawlCandidate.status)
            .order_by(CrawlCandidate.status.asc())
        )
    ).all()
    failure_rows = (
        await db.execute(
            select(Source, ThinkTank.name)
            .join(ThinkTank, ThinkTank.id == Source.think_tank_id)
            .where(Source.last_crawl_status == CrawlStatusEnum.failed)
            .order_by(Source.last_crawled_at.desc().nullslast(), Source.id.desc())
            .limit(5)
        )
    ).all()
    recent_report_rows = (
        await db.execute(
            select(Report.title)
            .where(Report.created_at >= since)
            .order_by(Report.created_at.desc(), Report.id.desc())
            .limit(5)
        )
    ).scalars().all()
    content_kind_rows = (
        await db.execute(
            select(Report.content_kind, func.count(Report.id))
            .where(Report.created_at >= since)
            .group_by(Report.content_kind)
            .order_by(func.count(Report.id).desc())
        )
    ).all()

    title = f"智库监测 {lookback_hours} 小时摘要"
    candidate_summary = "、".join(
        f"{get_candidate_status_label(status)} {int(count)}"
        for status, count in candidate_rows
    ) or "暂无候选报告更新"
    content_kind_summary = "、".join(
        f"{get_content_kind_label(content_kind)} {int(count)}"
        for content_kind, count in content_kind_rows
    ) or "暂无新增报告类型"
    report_lines = "\n".join(f"- {report_title}" for report_title in recent_report_rows)
    failure_lines = "\n".join(
        f"- {think_tank_name}：{source.last_error or '最近一次抓取失败'}"
        for source, think_tank_name in failure_rows
    )
    message_parts = [
        f"过去 {lookback_hours} 小时新增入库报告 {new_reports} 篇。",
        f"新增报告类型：{content_kind_summary}。",
        f"候选报告统计：{candidate_summary}。",
        f"AI 成果完成 {ai_completed_reports} 篇，失败 {ai_failed_reports} 篇。",
        f"当前失败来源 {failed_sources} 个。",
    ]

    if report_lines:
        message_parts.append(f"最新入库报告：\n{report_lines}")

    if failure_lines:
        message_parts.append(f"最近失败原因：\n{failure_lines}")

    return DailySummary(
        title=title,
        message="\n\n".join(message_parts),
        metrics={
            "new_reports": new_reports,
            "saved_candidates": saved_candidates,
            "skipped_candidates": skipped_candidates,
            "ai_completed_reports": ai_completed_reports,
            "ai_failed_reports": ai_failed_reports,
            "failed_sources": failed_sources,
        },
    )
