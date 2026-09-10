import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.session import AsyncSessionLocal
from app.models import CrawlCandidate, CrawlRun, Report, Source
from app.models.source import CrawlStatusEnum, SourceTypeEnum
from app.services.ai.report_relevance_service import (
    evaluate_china_relevance,
)
from app.services.crawl_candidate_service import (
    CANDIDATE_STATUS_DISCOVERED,
    mark_candidate_saved,
    mark_candidate_skipped,
)
from app.services.crawl_quality_service import CrawlQualityStats
from app.services.crawler.brookings_parser import (
    parse_brookings_reports,
)
from app.services.crawler.csis_analysis_parser import (
    parse_csis_reports,
)
from app.services.crawler.http_client import (
    fetch_html,
    fetch_resource,
)
from app.services.crawler.report_document_service import (
    fetch_report_document,
)
from app.services.crawler.rss_parser import parse_rss_articles
from app.services.notification_service import notification_service

BROOKINGS_DISCOVERY_URLS = (
    "https://www.brookings.edu/",
    "https://www.brookings.edu/regions/asia-the-pacific/china/",
)


def normalize_url(url: str) -> str | None:
    """
    将文章 URL 规范化，用于同一来源内的去重。

    当前规则：
    - 仅接受 http / https；
    - 协议、域名转小写；
    - 去除 fragment，例如 #section；
    - 保留 query 参数，避免误删有实际含义的 URL 参数；
    - 非根路径移除末尾 /。
    """
    value = url.strip()

    if not value:
        return None

    parsed = urlsplit(value)

    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"

    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    return urlunsplit(
        (
            scheme,
            netloc,
            path,
            parsed.query,
            "",
        )
    )


async def _fetch_source_articles(
    source: Source,
) -> list[dict[str, object]]:
    """
    根据 Source 类型读取候选报告条目。

    RSS 来源继续使用现有 RSS parser；
    website 来源目前仅支持 CSIS /analysis。
    """
    if source.source_type == SourceTypeEnum.rss:
        feed_content = await fetch_html(
            source.url
        )

        return parse_rss_articles(
            feed_content,
            source.url,
        )

    if source.source_type == SourceTypeEnum.website:
        hostname = urlsplit(
            source.url
        ).netloc.lower()

        if hostname in {
            "www.csis.org",
            "csis.org",
        }:
            resource = await fetch_resource(
                source.url
            )

            return parse_csis_reports(
                resource.content,
                resource.final_url,
            )

        if hostname in {
            "www.brookings.edu",
            "brookings.edu",
        }:
            articles_by_url: dict[str, dict[str, object]] = {}

            discovery_urls = (
                source.url,
                *(
                    url
                    for url in BROOKINGS_DISCOVERY_URLS
                    if url != source.url
                ),
            )

            for discovery_url in discovery_urls:
                resource = await fetch_resource(
                    discovery_url
                )

                for article in parse_brookings_reports(
                    resource.content,
                    resource.final_url,
                ):
                    url = str(article["url"])
                    articles_by_url.setdefault(
                        url,
                        article,
                    )

            return list(articles_by_url.values())

        raise ValueError(
            "当前尚未配置该 website 来源的专用解析器："
            f"{source.url}"
        )

    raise ValueError(
        "当前不支持此来源类型抓取："
        f"{source.source_type.value}"
    )


def crawl_source(source_id: int) -> dict[str, int | str]:
    """Celery 同步任务入口：抓取一个 RSS 来源。"""
    return asyncio.run(_crawl_source_async(source_id))


async def _crawl_source_async(source_id: int) -> dict[str, int | str]:
    run_id: int | None = None

    try:
        async with AsyncSessionLocal() as db:
            source = await db.get(Source, source_id)

            if source is None:
                raise ValueError(f"来源不存在: source_id={source_id}")

            if not source.is_active:
                raise ValueError(f"来源已停用: source_id={source_id}")

            if source.source_type not in {
                SourceTypeEnum.rss,
                SourceTypeEnum.website,
            }:
                raise ValueError(
                    "当前仅支持 RSS 和 website 来源抓取，"
                    f"实际类型为: {source.source_type.value}"
                )

            now = datetime.now(UTC)

            crawl_run = CrawlRun(
                source_id=source.id,
                status="running",
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

            parsed_articles = await _fetch_source_articles(
                source
            )

            quality_stats = CrawlQualityStats(
                raw_candidates=len(parsed_articles)
            )
            articles_by_url: dict[str, dict[str, object]] = {}
            candidates_by_url: dict[str, CrawlCandidate] = {}

            for article in parsed_articles:
                candidate = CrawlCandidate(
                    crawl_run_id=run_id,
                    source_id=source.id,
                    title=str(article.get("title", ""))[:500],
                    url=str(article["url"]),
                    status=CANDIDATE_STATUS_DISCOVERED,
                )
                db.add(candidate)

                normalized_url = normalize_url(str(article["url"]))

                if normalized_url is None:
                    mark_candidate_skipped(
                        candidate,
                        reason_code="invalid_url",
                    )
                    quality_stats.invalid_url += 1
                    quality_stats.add_sample(
                        "无效 URL",
                        article.get("url"),
                    )
                    continue

                candidate.normalized_url = normalized_url

                # 同一份 RSS 内，URL 重复时保留第一条。
                if normalized_url not in articles_by_url:
                    articles_by_url[normalized_url] = article
                    candidates_by_url[normalized_url] = candidate
                else:
                    mark_candidate_skipped(
                        candidate,
                        reason_code="duplicate_in_feed",
                    )
                    quality_stats.duplicate_in_feed += 1
                    quality_stats.add_sample(
                        "同源重复",
                        article.get("url"),
                    )

            normalized_urls = list(articles_by_url)
            quality_stats.unique_candidates = len(articles_by_url)

            existing_urls: set[str] = set()

            if normalized_urls:
                result = await db.execute(
                    select(Report.normalized_url).where(
                        Report.source_id == source.id,
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

                if normalized_url in existing_urls:
                    mark_candidate_skipped(
                        candidate,
                        reason_code="duplicate_existing",
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
                        reason_code="document_failed",
                        error=exc,
                    )
                    quality_stats.document_failed += 1
                    quality_stats.add_sample(
                        "PDF 获取或页数/文本检查失败",
                        article["url"],
                        exc,
                    )
                    print(
                        f"report skipped {article['url']}: {exc}"
                    )
                    continue

                content = document.text
                candidate.pdf_url = document.pdf_url
                candidate.page_count = document.page_count
                candidate.non_empty_page_count = document.non_empty_page_count
                candidate.pdf_byte_length = document.pdf_byte_length

                try:
                    relevance = await evaluate_china_relevance(
                        str(article["title"]),
                        content,
                    )
                except Exception as exc:
                    mark_candidate_skipped(
                        candidate,
                        reason_code="relevance_failed",
                        error=exc,
                    )
                    quality_stats.relevance_failed += 1
                    quality_stats.add_sample(
                        "涉华判断失败",
                        article["url"],
                        exc,
                    )
                    print(
                        f"relevance check failed "
                        f"{article['url']}: {exc}"
                    )
                    continue

                candidate.relevance = str(relevance.get("relevance", ""))[:30]
                candidate.relevance_reason = str(relevance.get("reason", ""))
                candidate.is_china_related = bool(relevance["is_china_related"])

                if not relevance["is_china_related"]:
                    mark_candidate_skipped(
                        candidate,
                        reason_code="non_china_related",
                        error=relevance.get("reason"),
                    )
                    quality_stats.non_china_related += 1
                    quality_stats.add_sample(
                        "非涉华",
                        article["url"],
                        relevance.get("reason"),
                    )
                    print(
                        f"report skipped as non-China-related "
                        f"{article['url']}: "
                        f"{relevance['relevance']} - "
                        f"{relevance['reason']}"
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
                    crawl_status="success",
                    content_fetched_at=content_fetched_at,
                    crawl_error=None,
                    published_at=article["published_at"],
                    ai_status="pending",
                    ai_retry_count=0,
                )

                try:
                    # 用 savepoint 防止极少数并发抓取造成的唯一键冲突中断整个任务。
                    async with db.begin_nested():
                        db.add(report)
                        await db.flush()
                        await notification_service.create_for_all_active_users(
                            db,
                            event_type="report.created",
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
                        reason_code="concurrent_duplicate",
                    )
                    quality_stats.concurrent_duplicate += 1
                    quality_stats.add_sample(
                        "并发重复入库",
                        article["url"],
                    )
                    continue

            finished_at = datetime.now(UTC)
            quality_stats.saved_reports = saved_count

            crawl_run.status = "success"
            crawl_run.found_count = len(articles_by_url)
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
                "found_count": len(articles_by_url),
                "saved_count": saved_count,
            }

    except Exception as exc:
        error_message = f"{type(exc).__name__}: {exc}"[:5000]

        if run_id is not None:
            async with AsyncSessionLocal() as db:
                source = await db.get(Source, source_id)
                crawl_run = await db.get(CrawlRun, run_id)

                if crawl_run is not None:
                    crawl_run.status = "failed"
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
            select(Source).where(
                Source.is_active.is_(True),
                Source.source_type.in_(
                    (
                        SourceTypeEnum.rss,
                        SourceTypeEnum.website,
                    )
                ),
            )
        )

        sources = list(result.scalars().all())

    now = datetime.now(UTC)

    return [
        source.id
        for source in sources
        if _is_source_due_for_crawl(
            source,
            now=now,
        )
    ]


def crawl_all_sources() -> int:
    """
    抓取所有启用且已到抓取时间的来源。

    返回新入库报告总数。
    """
    source_ids = asyncio.run(_get_due_source_ids())

    saved_count = 0

    for source_id in source_ids:
        try:
            result = crawl_source(source_id)
            saved_count += int(result["saved_count"])
        except Exception as exc:
            print(f"crawl failed source_id={source_id}: {exc}")

    return saved_count
