import argparse
import asyncio
import json

from app.models.source import Source, SourceTypeEnum
from app.models.think_tank import PriorityTierEnum
from app.scripts.seed_thinktank_data import SEED_THINK_TANKS
from app.scripts.source_governance import derive_source_governance
from app.services.crawler.source_article_discovery import fetch_source_articles

DEFAULT_TIERS = {
    PriorityTierEnum.p0,
    PriorityTierEnum.p1,
}


async def check_source(
    *,
    key: str,
    name: str,
    source_type: SourceTypeEnum,
    url: str,
    timeout_seconds: float,
) -> dict[str, object]:
    source = Source(
        think_tank_id=0,
        source_type=source_type,
        url=url,
        crawl_frequency_minutes=1440,
        is_active=True,
    )

    try:
        articles = await asyncio.wait_for(
            fetch_source_articles(source),
            timeout=timeout_seconds,
        )

        return {
            "key": key,
            "name": name,
            "source_type": source_type.value,
            "url": url,
            "status": "ok",
            "found": len(articles),
            "samples": [
                {
                    "title": str(article.get("title", ""))[:180],
                    "url": str(article.get("url", ""))[:240],
                    "content_type": str(article.get("content_type", "")),
                }
                for article in articles[:5]
            ],
        }

    except Exception as exc:
        return {
            "key": key,
            "name": name,
            "source_type": source_type.value,
            "url": url,
            "status": "error",
            "found": 0,
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
        }


def build_checks(
    *,
    tiers: set[PriorityTierEnum],
    timeout_seconds: float,
) -> list:
    checks = []

    for item in SEED_THINK_TANKS:
        tier, _region, is_verified = derive_source_governance(item)

        if tier not in tiers or not is_verified:
            continue

        key = str(item["key"])
        name = str(item.get("name_en") or item["name"])
        website = item.get("website")
        rss = item.get("rss")

        if website:
            checks.append(
                check_source(
                    key=key,
                    name=name,
                    source_type=SourceTypeEnum.website,
                    url=str(website),
                    timeout_seconds=timeout_seconds,
                )
            )

        if rss:
            checks.append(
                check_source(
                    key=key,
                    name=name,
                    source_type=SourceTypeEnum.rss,
                    url=str(rss),
                    timeout_seconds=timeout_seconds,
                )
            )

    return checks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "只读复核重点来源发现阶段：真实访问来源入口并统计候选条目，"
            "不写数据库、不下载 PDF、不调用 LLM。"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=75.0,
        help="单个来源发现阶段超时时间，单位秒。",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="同时复核的来源数量。",
    )
    return parser.parse_args()


async def main_async() -> None:
    args = parse_args()
    semaphore = asyncio.Semaphore(
        max(
            1,
            args.concurrency,
        )
    )

    async def limited_check(check):
        async with semaphore:
            return await check

    results = await asyncio.gather(
        *[
            limited_check(check)
            for check in build_checks(
                tiers=DEFAULT_TIERS,
                timeout_seconds=args.timeout,
            )
        ]
    )
    results.sort(
        key=lambda row: (
            str(row["key"]),
            str(row["source_type"]),
        )
    )
    print(json.dumps(results, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main_async())
