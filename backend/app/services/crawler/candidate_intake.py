from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.status import CrawlCandidateSkipReason
from app.models import CrawlCandidate
from app.services.crawl_candidate_service import (
    CANDIDATE_STATUS_DISCOVERED,
    mark_candidate_skipped,
)
from app.services.crawl_quality_service import CrawlQualityStats


@dataclass(frozen=True)
class CandidateIntakeResult:
    articles_by_url: dict[str, dict[str, object]]
    candidates_by_url: dict[str, CrawlCandidate]


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


def intake_crawl_candidates(
    db: AsyncSession,
    *,
    parsed_articles: list[dict[str, object]],
    crawl_run_id: int,
    source_id: int,
    quality_stats: CrawlQualityStats,
) -> CandidateIntakeResult:
    articles_by_url: dict[str, dict[str, object]] = {}
    candidates_by_url: dict[str, CrawlCandidate] = {}

    for article in parsed_articles:
        candidate = CrawlCandidate(
            crawl_run_id=crawl_run_id,
            source_id=source_id,
            title=str(article.get("title", ""))[:500],
            url=str(article["url"]),
            status=CANDIDATE_STATUS_DISCOVERED,
        )
        db.add(candidate)

        normalized_url = normalize_url(str(article["url"]))

        if normalized_url is None:
            mark_candidate_skipped(
                candidate,
                reason_code=CrawlCandidateSkipReason.invalid_url.value,
            )
            quality_stats.invalid_url += 1
            quality_stats.add_sample(
                "无效 URL",
                article.get("url"),
            )
            continue

        candidate.normalized_url = normalized_url

        # 同一份来源结果内，URL 重复时保留第一条。
        if normalized_url not in articles_by_url:
            articles_by_url[normalized_url] = article
            candidates_by_url[normalized_url] = candidate
        else:
            mark_candidate_skipped(
                candidate,
                reason_code=CrawlCandidateSkipReason.duplicate_in_feed.value,
            )
            quality_stats.duplicate_in_feed += 1
            quality_stats.add_sample(
                "同源重复",
                article.get("url"),
            )

    quality_stats.unique_candidates = len(articles_by_url)

    return CandidateIntakeResult(
        articles_by_url=articles_by_url,
        candidates_by_url=candidates_by_url,
    )
