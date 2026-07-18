import asyncio
from datetime import UTC, datetime
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.session import AsyncSessionLocal
from app.models import CrawlRun, Report, Source
from app.models.source import CrawlStatusEnum, SourceTypeEnum
from app.services.crawler.http_client import fetch_html
from app.services.crawler.rss_parser import parse_rss_articles


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

            if source.source_type != SourceTypeEnum.rss:
                raise ValueError(
                    f"当前仅支持 RSS 来源抓取，实际类型为: {source.source_type.value}"
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

            feed_content = await fetch_html(source.url)
            parsed_articles = parse_rss_articles(feed_content, source.url)

            articles_by_url: dict[str, dict[str, object]] = {}

            for article in parsed_articles:
                normalized_url = normalize_url(str(article["url"]))

                if normalized_url is None:
                    continue

                # 同一份 RSS 内，URL 重复时保留第一条。
                if normalized_url not in articles_by_url:
                    articles_by_url[normalized_url] = article

            normalized_urls = list(articles_by_url)

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
                if normalized_url in existing_urls:
                    continue

                report = Report(
                    source_id=source.id,
                    title=str(article["title"])[:500],
                    url=str(article["url"]),
                    normalized_url=normalized_url,
                    content=(
                        str(article["content"])
                        if article["content"] is not None
                        else None
                    ),
                    published_at=article["published_at"],
                    analysis_status="pending",
                )

                try:
                    # 用 savepoint 防止极少数并发抓取造成的唯一键冲突中断整个任务。
                    async with db.begin_nested():
                        db.add(report)
                        await db.flush()

                    saved_count += 1
                except IntegrityError:
                    # 另一任务已写入同 URL 时，视为正常去重。
                    continue

            finished_at = datetime.now(UTC)

            crawl_run.status = "success"
            crawl_run.found_count = len(articles_by_url)
            crawl_run.saved_count = saved_count
            crawl_run.error = None
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


async def _get_active_rss_source_ids() -> list[int]:
    """获取所有启用的 RSS 来源 ID。"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Source.id).where(
                Source.is_active.is_(True),
                Source.source_type == SourceTypeEnum.rss,
            )
        )
        return list(result.scalars().all())


def crawl_all_sources() -> int:
    """
    抓取所有启用的 RSS 来源。

    返回新入库报告总数。
    """
    source_ids = asyncio.run(_get_active_rss_source_ids())

    saved_count = 0

    for source_id in source_ids:
        try:
            result = crawl_source(source_id)
            saved_count += int(result["saved_count"])
        except Exception as exc:
            print(f"crawl failed source_id={source_id}: {exc}")

    return saved_count
