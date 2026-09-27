from __future__ import annotations

import argparse
import asyncio
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.status import (
    CrawlCandidateSkipReason,
    CrawlRunStatus,
    NotificationEventType,
    ReportAIStatus,
    ReportCrawlStatus,
)
from app.db.session import AsyncSessionLocal
from app.models import CrawlRun, Report, Source, ThinkTank
from app.models.source import CrawlStatusEnum, SourceTypeEnum
from app.services.crawl_candidate_service import (
    mark_candidate_saved,
    mark_candidate_skipped,
)
from app.services.crawl_quality_service import CrawlQualityStats
from app.services.crawler.candidate_intake import intake_crawl_candidates
from app.services.crawler.report_document_service import fetch_report_document
from app.services.crawler.source_article_discovery import fetch_source_articles
from app.services.notification_service import notification_service
from app.services.source_rollout_policy import (
    ROLLOUT_STAGE_STANDARD_REVIEW,
    get_source_rollout_policy,
)

DEFAULT_KEYS = (
    "cfr",
    "heritage",
)


@dataclass(frozen=True)
class PilotSource:
    key: str
    name: str
    source: Source


def parse_keys(value: str) -> list[str]:
    return [
        key.strip().lower()
        for key in value.split(",")
        if key.strip()
    ]


def ensure_pilot_allowed(
    keys: list[str],
    *,
    allow_standard_review: bool = False,
) -> None:
    blocked = [
        key
        for key in keys
        if not (
            get_source_rollout_policy(key).can_run_pilot_crawl
            or (
                allow_standard_review
                and get_source_rollout_policy(key).rollout_stage
                == ROLLOUT_STAGE_STANDARD_REVIEW
            )
        )
    ]

    if blocked:
        raise ValueError(
            "以下来源尚未允许进入入库试运行："
            + ", ".join(blocked)
        )


async def load_pilot_sources(
    keys: list[str],
    *,
    allow_standard_review: bool = False,
) -> list[PilotSource]:
    ensure_pilot_allowed(
        keys,
        allow_standard_review=allow_standard_review,
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(
                ThinkTank.key,
                ThinkTank.name_en,
                ThinkTank.name,
                Source,
            )
            .join(Source, Source.think_tank_id == ThinkTank.id)
            .where(
                ThinkTank.key.in_(keys),
                Source.source_type == SourceTypeEnum.website,
                Source.is_active.is_(True),
            )
            .order_by(ThinkTank.key.asc())
        )

        rows = result.all()

    sources: list[PilotSource] = []
    seen_keys: set[str] = set()

    for key, name_en, name, source in rows:
        if key in seen_keys:
            continue

        sources.append(
            PilotSource(
                key=key,
                name=str(name_en or name or key),
                source=source,
            )
        )
        seen_keys.add(key)

    found_keys = {
        source.key
        for source in sources
    }
    missing_keys = [
        key
        for key in keys
        if key not in found_keys
    ]

    if missing_keys:
        raise ValueError(
            "数据库中未找到可用 website 来源："
            + ", ".join(missing_keys)
        )

    return sources


async def pilot_crawl_source(
    pilot_source: PilotSource,
    *,
    max_saved: int,
    max_candidates: int,
    notify: bool,
    ai_status: str,
) -> dict[str, object]:
    now = datetime.now(UTC)
    source = pilot_source.source

    async with AsyncSessionLocal() as db:
        db.add(source)
        crawl_run = CrawlRun(
            source_id=source.id,
            status=CrawlRunStatus.running.value,
            found_count=0,
            saved_count=0,
            started_at=now.replace(tzinfo=None),
        )
        db.add(crawl_run)
        await db.commit()
        await db.refresh(crawl_run)

        parsed_articles = await fetch_source_articles(source)
        selected_articles = parsed_articles[:max_candidates]
        quality_stats = CrawlQualityStats(
            raw_candidates=len(parsed_articles)
        )
        candidate_intake = intake_crawl_candidates(
            db,
            parsed_articles=selected_articles,
            crawl_run_id=crawl_run.id,
            source_id=source.id,
            quality_stats=quality_stats,
        )
        articles_by_url = candidate_intake.articles_by_url
        candidates_by_url = candidate_intake.candidates_by_url
        normalized_urls = list(articles_by_url)

        existing_urls: set[str] = set()

        if normalized_urls:
            result = await db.execute(
                select(Report.normalized_url).where(
                    Report.normalized_url.in_(normalized_urls),
                )
            )
            existing_urls = {
                normalized_url
                for normalized_url in result.scalars().all()
                if normalized_url is not None
            }

        saved_count = 0

        for normalized_url, article in articles_by_url.items():
            candidate = candidates_by_url[normalized_url]

            if saved_count >= max_saved:
                break

            if normalized_url in existing_urls:
                mark_candidate_skipped(
                    candidate,
                    reason_code=CrawlCandidateSkipReason.duplicate_existing.value,
                )
                quality_stats.duplicate_existing += 1
                quality_stats.add_sample(
                    "已入库重复",
                    article["url"],
                )
                continue

            try:
                document = await fetch_report_document(
                    str(article["url"]),
                    allow_web_article_fallback=bool(
                        article.get(
                            "allow_web_article_fallback",
                            False,
                        )
                    ),
                )
            except Exception as exc:
                mark_candidate_skipped(
                    candidate,
                    reason_code=CrawlCandidateSkipReason.document_failed.value,
                    error=exc,
                )
                quality_stats.document_failed += 1
                quality_stats.add_sample(
                    "PDF 获取或页数/文本检查失败",
                    article["url"],
                    exc,
                )
                continue

            content_hash = hashlib.sha256(
                document.text.encode("utf-8")
            ).hexdigest()
            content_fetched_at = datetime.now(UTC).replace(tzinfo=None)

            report = Report(
                source_id=source.id,
                title=str(article["title"])[:500],
                url=str(article["url"]),
                normalized_url=normalized_url,
                content_hash=content_hash,
                content=document.text,
                pdf_url=document.pdf_url,
                page_count=document.page_count,
                non_empty_page_count=document.non_empty_page_count,
                pdf_byte_length=document.pdf_byte_length,
                content_kind=document.content_kind,
                crawl_status=ReportCrawlStatus.success.value,
                content_fetched_at=content_fetched_at,
                crawl_error=None,
                published_at=article["published_at"],
                ai_status=ai_status,
                ai_retry_count=0,
            )

            try:
                async with db.begin_nested():
                    db.add(report)
                    await db.flush()

                    if notify:
                        await notification_service.create_for_all_active_users(
                            db,
                            event_type=NotificationEventType.report_created.value,
                            title="试运行发现新的涉华智库报告",
                            message=f"{report.title}",
                            report_id=report.id,
                        )

                    mark_candidate_saved(
                        candidate,
                        report_id=report.id,
                    )
                    candidate.pdf_url = document.pdf_url
                    candidate.page_count = document.page_count
                    candidate.non_empty_page_count = document.non_empty_page_count
                    candidate.pdf_byte_length = document.pdf_byte_length
                    candidate.content_kind = document.content_kind

                saved_count += 1
            except IntegrityError:
                mark_candidate_skipped(
                    candidate,
                    reason_code=CrawlCandidateSkipReason.concurrent_duplicate.value,
                )
                quality_stats.concurrent_duplicate += 1
                quality_stats.add_sample(
                    "并发重复入库",
                    article["url"],
                )

        finished_at = datetime.now(UTC)
        quality_stats.saved_reports = saved_count
        crawl_run.status = CrawlRunStatus.success.value
        crawl_run.found_count = len(articles_by_url)
        crawl_run.saved_count = saved_count
        crawl_run.error = quality_stats.to_summary()
        crawl_run.finished_at = finished_at.replace(tzinfo=None)
        source.last_crawl_status = CrawlStatusEnum.success
        source.last_crawled_at = finished_at
        source.last_error = None

        await db.commit()

        return {
            "key": pilot_source.key,
            "name": pilot_source.name,
            "source_id": source.id,
            "crawl_run_id": crawl_run.id,
            "found_count": len(articles_by_url),
            "saved_count": saved_count,
            "summary": crawl_run.error,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "小批量真实入库试运行：仅允许 pilot_crawl 来源，"
            "限制保存数量，默认不发通知、不排 AI。"
        ),
    )
    parser.add_argument(
        "--keys",
        default=",".join(DEFAULT_KEYS),
        help="逗号分隔的机构 key，默认 cfr,heritage。",
    )
    parser.add_argument(
        "--max-saved",
        type=int,
        default=1,
        help="每个来源最多保存报告数，默认 1。",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=5,
        help="每个来源最多检查候选数，默认 5。",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="保存报告后创建站内通知；默认不通知。",
    )
    parser.add_argument(
        "--allow-standard-review",
        action="store_true",
        help=(
            "允许 standard_review 来源进行人工小样本试写；"
            "blocked 和 discovery_only 来源仍会被拒绝。"
        ),
    )
    parser.add_argument(
        "--ai-status",
        choices=[
            ReportAIStatus.pending.value,
            ReportAIStatus.skipped.value,
        ],
        default=ReportAIStatus.skipped.value,
        help="新报告 AI 状态，默认 skipped，避免自动排队。",
    )
    return parser.parse_args()


async def main_async() -> None:
    args = parse_args()
    keys = parse_keys(args.keys)
    max_saved = max(
        1,
        args.max_saved,
    )
    max_candidates = max(
        max_saved,
        args.max_candidates,
    )
    pilot_sources = await load_pilot_sources(
        keys,
        allow_standard_review=args.allow_standard_review,
    )
    results = []

    for pilot_source in pilot_sources:
        results.append(
            await pilot_crawl_source(
                pilot_source,
                max_saved=max_saved,
                max_candidates=max_candidates,
                notify=args.notify,
                ai_status=args.ai_status,
            )
        )

    for result in results:
        print(result)


if __name__ == "__main__":
    asyncio.run(main_async())
