import asyncio
import hashlib
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.core.llm_authorization import LLMNotAuthorized
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
from app.services.ai.report_relevance_service import (
    evaluate_china_relevance,
)
from app.services.crawl_candidate_service import (
    mark_candidate_pending_relevance,
    mark_candidate_saved,
    mark_candidate_skipped,
    set_candidate_document_metadata,
)
from app.services.crawl_lock import crawl_execution_lock
from app.services.crawl_quality_service import CrawlQualityStats
from app.services.crawler import source_article_discovery
from app.services.crawler.candidate_duplicate_service import (
    build_candidate_duplicate_index,
    mark_duplicate_candidate,
)
from app.services.crawler.candidate_intake import (
    intake_crawl_candidates,
)
from app.services.crawler.candidate_intake import (
    normalize_url as _normalize_url,
)
from app.services.crawler.http_client import fetch_html, fetch_resource
from app.services.crawler.report_document_service import (
    fetch_report_document,
)
from app.services.notification_service import notification_service
from app.services.source_rollout_policy import get_source_rollout_policy

SOURCE_DISCOVERY_TIMEOUT_SECONDS = 90.0
REPORT_DOCUMENT_FETCH_TIMEOUT_SECONDS = 90.0
REPORT_RELEVANCE_TIMEOUT_SECONDS = 60.0

logger = logging.getLogger(__name__)


async def _fetch_source_articles(
    source: Source,
) -> list[dict[str, object]]:
    # Keep the old crawler_service monkeypatch seam while the implementation
    # lives in the dedicated discovery module.
    source_article_discovery.fetch_html = fetch_html
    source_article_discovery.fetch_resource = fetch_resource
    return await source_article_discovery.fetch_source_articles(source)


def normalize_url(url: str) -> str | None:
    return _normalize_url(url)


def crawl_source(source_id: int) -> dict[str, int | str]:
    """Celery 同步任务入口：互斥抓取一个来源。"""
    return asyncio.run(_crawl_source_async(source_id))


def _ensure_source_rollout_allowed(
    *,
    source: Source,
    think_tank: ThinkTank | None,
) -> None:
    if think_tank is None:
        raise ValueError(
            "来源未关联智库，不能执行自动入库抓取: "
            f"source_id={source.id}"
        )

    rollout_policy = get_source_rollout_policy(
        think_tank.key
    )

    if not rollout_policy.can_run_pilot_crawl:
        raise ValueError(
            "来源尚未允许进入自动入库抓取: "
            f"key={think_tank.key}, "
            f"stage={rollout_policy.rollout_stage}"
        )


def _skipped_source_result(source_id: int, reason: str) -> dict[str, int | str]:
    return {
        "status": "skipped",
        "source_id": source_id,
        "reason": reason,
        "found_count": 0,
        "saved_count": 0,
    }


async def _crawl_source_async(
    source_id: int,
    *,
    only_if_due: bool = False,
) -> dict[str, int | str]:
    async with crawl_execution_lock(source_id) as acquired:
        if not acquired:
            return _skipped_source_result(source_id, "already_running")
        return await _crawl_source_locked_async(source_id, only_if_due=only_if_due)


async def _crawl_source_locked_async(
    source_id: int,
    *,
    only_if_due: bool,
) -> dict[str, int | str]:
    run_id: int | None = None

    try:
        async with AsyncSessionLocal() as db:
            source = await db.get(Source, source_id)

            if source is None:
                if only_if_due:
                    return _skipped_source_result(source_id, "source_missing")
                raise ValueError(f"来源不存在: source_id={source_id}")

            if not source.is_active:
                if only_if_due:
                    return _skipped_source_result(source_id, "source_disabled")
                raise ValueError(f"来源已停用: source_id={source_id}")

            if source.source_type not in {
                SourceTypeEnum.rss,
                SourceTypeEnum.website,
            }:
                if only_if_due:
                    return _skipped_source_result(source_id, "unsupported_source_type")
                raise ValueError(
                    "当前仅支持 RSS 和 website 来源抓取，"
                    f"实际类型为: {source.source_type.value}"
                )

            think_tank = await db.get(
                ThinkTank,
                source.think_tank_id,
            )

            if only_if_due and (
                think_tank is None
                or not get_source_rollout_policy(think_tank.key).can_run_pilot_crawl
            ):
                return _skipped_source_result(source_id, "rollout_not_allowed")

            _ensure_source_rollout_allowed(
                source=source,
                think_tank=think_tank,
            )

            now = datetime.now(UTC)

            if only_if_due and not _is_source_due_for_crawl(source, now=now):
                return _skipped_source_result(source_id, "not_due")

            # Acquiring the source lock proves earlier locked executions have ended.
            await db.execute(
                update(CrawlRun)
                .where(
                    CrawlRun.source_id == source.id,
                    CrawlRun.status == CrawlRunStatus.running.value,
                )
                .values(
                    status=CrawlRunStatus.failed.value,
                    error="上次抓取中断，已在获得来源执行锁后恢复。",
                    finished_at=now.replace(tzinfo=None),
                )
            )

            crawl_run = CrawlRun(
                source_id=source.id,
                status=CrawlRunStatus.running.value,
                found_count=0,
                saved_count=0,
                started_at=now.replace(tzinfo=None),
            )

            db.add(crawl_run)

            source.last_crawl_status = CrawlStatusEnum.running
            source.last_error = None

            await db.commit()
            await db.refresh(crawl_run)

            run_id = crawl_run.id

            parsed_articles = await asyncio.wait_for(
                _fetch_source_articles(
                    source
                ),
                timeout=SOURCE_DISCOVERY_TIMEOUT_SECONDS,
            )

            quality_stats = CrawlQualityStats(
                raw_candidates=len(parsed_articles)
            )
            candidate_intake = intake_crawl_candidates(
                db,
                parsed_articles=parsed_articles,
                crawl_run_id=run_id,
                source_id=source.id,
                quality_stats=quality_stats,
            )

            articles_by_url = candidate_intake.articles_by_url
            candidates_by_url = candidate_intake.candidates_by_url
            found_count = candidate_intake.unique_candidate_count

            duplicate_index = await build_candidate_duplicate_index(
                db,
                candidates=candidates_by_url.values(),
                exclude_crawl_run_id=run_id,
            )

            saved_count = 0

            for normalized_url, article in articles_by_url.items():
                candidate = candidates_by_url[normalized_url]

                if mark_duplicate_candidate(
                    candidate,
                    duplicate_kind=duplicate_index.classify(candidate),
                    quality_stats=quality_stats,
                    url=article["url"],
                ):
                    continue

                try:
                    document = await asyncio.wait_for(
                        fetch_report_document(
                            str(article["url"]),
                            allow_web_article_fallback=bool(
                                article.get(
                                    "allow_web_article_fallback",
                                    False,
                                )
                            ),
                        ),
                        timeout=REPORT_DOCUMENT_FETCH_TIMEOUT_SECONDS,
                    )
                except Exception as exc:
                    mark_candidate_skipped(
                        candidate,
                        reason_code=CrawlCandidateSkipReason.document_failed.value,
                        error=exc,
                    )
                    quality_stats.add_document_failure_sample(
                        article["url"],
                        exc,
                    )
                    logger.warning(
                        "Report candidate skipped after document fetch "
                        "failed: source_id=%s crawl_run_id=%s url=%s "
                        "error=%r",
                        source.id,
                        run_id,
                        article["url"],
                        exc,
                    )
                    continue

                content = document.text
                set_candidate_document_metadata(candidate, document)

                document_duplicate_index = await build_candidate_duplicate_index(
                    db,
                    candidates=[candidate],
                    exclude_crawl_run_id=run_id,
                )
                if mark_duplicate_candidate(
                    candidate,
                    duplicate_kind=document_duplicate_index.classify(candidate),
                    quality_stats=quality_stats,
                    url=article["url"],
                ):
                    continue

                try:
                    relevance = await asyncio.wait_for(
                        evaluate_china_relevance(
                            candidate.title or "",
                            content,
                            source_id=source.id,
                            normalized_url=normalized_url,
                        ),
                        timeout=REPORT_RELEVANCE_TIMEOUT_SECONDS,
                    )
                except LLMNotAuthorized as exc:
                    mark_candidate_pending_relevance(candidate, error=exc)
                    quality_stats.pending_relevance += 1
                    continue
                except Exception as exc:
                    mark_candidate_skipped(
                        candidate,
                        reason_code=CrawlCandidateSkipReason.relevance_failed.value,
                        error=exc,
                    )
                    quality_stats.relevance_failed += 1
                    quality_stats.add_sample(
                        "涉华判断失败",
                        article["url"],
                        exc,
                    )
                    logger.warning(
                        "Report candidate skipped after relevance check "
                        "failed: source_id=%s crawl_run_id=%s url=%s "
                        "error=%r",
                        source.id,
                        run_id,
                        article["url"],
                        exc,
                    )
                    continue

                candidate.relevance = str(relevance.get("relevance", ""))[:30]
                candidate.relevance_reason = str(relevance.get("reason", ""))
                candidate.is_china_related = bool(relevance["is_china_related"])

                if not relevance["is_china_related"]:
                    mark_candidate_skipped(
                        candidate,
                        reason_code=CrawlCandidateSkipReason.non_china_related.value,
                        error=relevance.get("reason"),
                    )
                    quality_stats.non_china_related += 1
                    quality_stats.add_sample(
                        "非涉华",
                        article["url"],
                        relevance.get("reason"),
                    )
                    logger.info(
                        "Report candidate skipped as non-China-related: "
                        "source_id=%s crawl_run_id=%s url=%s relevance=%s "
                        "reason=%s",
                        source.id,
                        run_id,
                        article["url"],
                        relevance["relevance"],
                        relevance["reason"],
                    )
                    continue

                content_hash = hashlib.sha256(
                    content.encode("utf-8")
                ).hexdigest()

                content_fetched_at = datetime.now(UTC).replace(
                    tzinfo=None
                )

                report = Report(
                    source_id=source.id,
                    title=str(article["title"])[:500],
                    url=str(article["url"]),
                    normalized_url=normalized_url,
                    content_hash=content_hash,
                    content=content,
                    pdf_url=document.pdf_url,
                    page_count=document.page_count,
                    non_empty_page_count=document.non_empty_page_count,
                    pdf_byte_length=document.pdf_byte_length,
                    content_kind=document.content_kind,
                    crawl_status=ReportCrawlStatus.success.value,
                    content_fetched_at=content_fetched_at,
                    crawl_error=None,
                    published_at=article["published_at"],
                    ai_status=ReportAIStatus.pending.value,
                    ai_retry_count=0,
                )

                try:
                    # 用 savepoint 防止极少数并发抓取造成的唯一键冲突中断整个任务。
                    async with db.begin_nested():
                        db.add(report)
                        await db.flush()
                        await notification_service.create_for_all_active_users(
                            db,
                            event_type=NotificationEventType.report_created.value,
                            title="发现新的涉华智库报告",
                            message=f"{report.title}",
                            report_id=report.id,
                        )
                        mark_candidate_saved(
                            candidate,
                            report_id=report.id,
                        )

                    saved_count += 1
                except IntegrityError:
                    # 另一任务已写入同 URL 时，视为正常去重。
                    mark_candidate_skipped(
                        candidate,
                        reason_code=CrawlCandidateSkipReason.concurrent_duplicate.value,
                    )
                    quality_stats.concurrent_duplicate += 1
                    quality_stats.add_sample(
                        "并发重复入库",
                        article["url"],
                    )
                    continue

            finished_at = datetime.now(UTC)
            quality_stats.saved_reports = saved_count

            crawl_run.status = CrawlRunStatus.success.value
            crawl_run.found_count = found_count
            crawl_run.saved_count = saved_count
            crawl_run.error = quality_stats.to_summary()
            crawl_run.finished_at = finished_at.replace(tzinfo=None)

            source.last_crawl_status = CrawlStatusEnum.success
            source.last_crawled_at = finished_at
            source.last_error = None

            await db.commit()

            return {
                "status": "success",
                "source_id": source.id,
                "found_count": found_count,
                "saved_count": saved_count,
            }

    except Exception as exc:
        error_message = f"{type(exc).__name__}: {exc}"[:5000]

        if run_id is not None:
            async with AsyncSessionLocal() as db:
                source = await db.get(Source, source_id)
                crawl_run = await db.get(CrawlRun, run_id)

                if crawl_run is not None:
                    crawl_run.status = CrawlRunStatus.failed.value
                    crawl_run.error = error_message
                    crawl_run.finished_at = datetime.now(UTC).replace(
                        tzinfo=None
                    )

                if source is not None:
                    source.last_crawl_status = CrawlStatusEnum.failed
                    source.last_crawled_at = datetime.now(UTC)
                    source.last_error = error_message

                await db.commit()

        raise


def _as_utc_aware(value: datetime | None) -> datetime | None:
    """将数据库时间统一为可比较的 UTC aware datetime。"""
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def _is_source_due_for_crawl(
    source: Source,
    *,
    now: datetime,
) -> bool:
    """判断来源是否达到下一次抓取时间。"""
    last_crawled_at = _as_utc_aware(
        source.last_crawled_at
    )

    if last_crawled_at is None:
        return True

    frequency_minutes = max(
        5,
        source.crawl_frequency_minutes or 1440,
    )

    return (
        last_crawled_at
        + timedelta(minutes=frequency_minutes)
        <= now
    )


async def _get_due_source_ids() -> list[int]:
    """获取所有启用且已到抓取时间的来源 ID。"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Source, ThinkTank.key)
            .join(ThinkTank, ThinkTank.id == Source.think_tank_id)
            .where(
                Source.is_active.is_(True),
                Source.source_type.in_(
                    (
                        SourceTypeEnum.rss,
                        SourceTypeEnum.website,
                    )
                ),
            )
            .order_by(Source.last_crawled_at.asc().nullsfirst(), Source.id)
        )

        sources = list(result.all())

    now = datetime.now(UTC)

    return [
        source.id
        for source, key in sources
        if get_source_rollout_policy(key).can_run_pilot_crawl
        and _is_source_due_for_crawl(
            source,
            now=now,
        )
    ]


def crawl_all_sources() -> dict[str, int | str]:
    """抓取已准入且到期的来源，返回批次统计。"""
    return asyncio.run(_crawl_all_sources_async())


async def _crawl_all_sources_async() -> dict[str, int | str]:
    summary: dict[str, int | str] = {
        "status": "success",
        "selected_count": 0,
        "completed_count": 0,
        "skipped_count": 0,
        "failed_count": 0,
        "saved_count": 0,
    }
    async with crawl_execution_lock() as acquired:
        if not acquired:
            return {**summary, "status": "skipped", "reason": "already_running"}

        source_ids = await _get_due_source_ids()
        summary["selected_count"] = len(source_ids)
        for source_id in source_ids:
            try:
                result = await _crawl_source_async(source_id, only_if_due=True)
                if result["status"] == "skipped":
                    summary["skipped_count"] = int(summary["skipped_count"]) + 1
                    logger.info(
                        "Scheduled source crawl skipped: source_id=%s reason=%s",
                        source_id,
                        result["reason"],
                    )
                else:
                    summary["completed_count"] = int(summary["completed_count"]) + 1
                    summary["saved_count"] = int(summary["saved_count"]) + int(result["saved_count"])
            except Exception as exc:
                summary["failed_count"] = int(summary["failed_count"]) + 1
                logger.exception(
                    "Scheduled source crawl failed: source_id=%s error=%r",
                    source_id,
                    exc,
                )

        if summary["failed_count"]:
            summary["status"] = (
                "failed"
                if summary["failed_count"] == summary["selected_count"]
                else "partial_failure"
            )
        logger.info("Scheduled crawl batch finished: %s", summary)
        return summary
