from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Iterable

from app.models.source import Source, SourceTypeEnum
from app.scripts.seed_thinktank_data import SEED_THINK_TANKS
from app.services.crawler.candidate_intake import normalize_url
from app.services.crawler.report_document_service import fetch_report_document
from app.services.crawler.source_article_discovery import fetch_source_articles
from app.services.source_rollout_policy import get_source_rollout_policy

DEFAULT_KEYS = (
    "aei",
    "heritage",
    "cfr",
)


def _source_from_seed_item(item: dict[str, object]) -> Source | None:
    website = item.get("website")

    if not website:
        return None

    return Source(
        think_tank_id=0,
        source_type=SourceTypeEnum.website,
        url=str(website),
        crawl_frequency_minutes=1440,
        is_active=True,
    )


def build_sources(keys: Iterable[str]) -> list[tuple[str, str, Source]]:
    key_set = {
        key.strip()
        for key in keys
        if key.strip()
    }
    sources: list[tuple[str, str, Source]] = []

    for item in SEED_THINK_TANKS:
        key = str(item["key"])

        if key not in key_set:
            continue

        source = _source_from_seed_item(item)

        if source is None:
            continue

        name = str(
            item.get("name_en")
            or item.get("name")
            or key
        )
        sources.append(
            (
                key,
                name,
                source,
            )
        )

    return sources


def deduplicate_articles(
    articles: list[dict[str, object]],
) -> tuple[list[dict[str, object]], int]:
    unique_articles: list[dict[str, object]] = []
    seen_urls: set[str] = set()
    duplicate_count = 0

    for article in articles:
        normalized_url = normalize_url(
            str(article.get("url", ""))
        )

        if normalized_url is None:
            continue

        if normalized_url in seen_urls:
            duplicate_count += 1
            continue

        seen_urls.add(normalized_url)
        unique_articles.append(article)

    return unique_articles, duplicate_count


async def audit_source_documents(
    *,
    key: str,
    name: str,
    source: Source,
    discovery_timeout_seconds: float,
    document_timeout_seconds: float,
    max_candidates: int,
) -> dict[str, object]:
    rollout_policy = get_source_rollout_policy(key)

    try:
        discovered_articles = await asyncio.wait_for(
            fetch_source_articles(source),
            timeout=discovery_timeout_seconds,
        )
    except Exception as exc:
        return {
            "key": key,
            "name": name,
            "url": source.url,
            "status": "discovery_error",
            "rollout_stage": rollout_policy.rollout_stage,
            "document_policy": rollout_policy.document_policy,
            "can_run_pilot_crawl": rollout_policy.can_run_pilot_crawl,
            "rollout_advice": rollout_policy.advice,
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
        }

    unique_articles, duplicate_count = deduplicate_articles(
        discovered_articles
    )
    checked_articles = unique_articles[:max_candidates]

    document_ok = 0
    document_failed = 0
    samples: list[dict[str, object]] = []

    for article in checked_articles:
        sample = {
            "title": str(article.get("title", ""))[:180],
            "url": str(article.get("url", ""))[:240],
            "content_type": str(article.get("content_type", "")),
        }

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
                timeout=document_timeout_seconds,
            )
        except Exception as exc:
            document_failed += 1
            sample.update(
                {
                    "status": "document_failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:300],
                }
            )
        else:
            document_ok += 1
            sample.update(
                {
                    "status": "document_ok",
                    "content_kind": document.content_kind,
                    "pdf_url": document.pdf_url,
                    "page_count": document.page_count,
                    "non_empty_page_count": document.non_empty_page_count,
                    "text_length": len(document.text),
                }
            )

        samples.append(sample)

    return {
        "key": key,
        "name": name,
        "url": source.url,
        "status": "ok",
        "rollout_stage": rollout_policy.rollout_stage,
        "document_policy": rollout_policy.document_policy,
        "can_run_pilot_crawl": rollout_policy.can_run_pilot_crawl,
        "rollout_advice": rollout_policy.advice,
        "raw_candidates": len(discovered_articles),
        "unique_candidates": len(unique_articles),
        "duplicate_candidates": duplicate_count,
        "checked_candidates": len(checked_articles),
        "document_ok": document_ok,
        "document_failed": document_failed,
        "samples": samples,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "只读复核重点来源抓取闭环：发现候选、获取 PDF/长文、检查 "
            "20 页门槛；不写数据库、不发通知、不调用 LLM。"
        ),
    )
    parser.add_argument(
        "--keys",
        default=",".join(DEFAULT_KEYS),
        help="逗号分隔的机构 key，默认 aei,heritage,cfr。",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=3,
        help="每个来源最多检查的候选数，默认 3。",
    )
    parser.add_argument(
        "--discovery-timeout",
        type=float,
        default=90.0,
        help="每个来源发现阶段超时时间，单位秒。",
    )
    parser.add_argument(
        "--document-timeout",
        type=float,
        default=120.0,
        help="每个候选文档获取阶段超时时间，单位秒。",
    )
    return parser.parse_args()


async def main_async() -> None:
    args = parse_args()
    keys = [
        key.strip()
        for key in args.keys.split(",")
        if key.strip()
    ]
    max_candidates = max(
        1,
        args.max_candidates,
    )

    results = []

    for key, name, source in build_sources(keys):
        results.append(
            await audit_source_documents(
                key=key,
                name=name,
                source=source,
                discovery_timeout_seconds=args.discovery_timeout,
                document_timeout_seconds=args.document_timeout,
                max_candidates=max_candidates,
            )
        )

    print(
        json.dumps(
            results,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    asyncio.run(main_async())
