from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import Source
from app.services.crawler.http_client import fetch_html
from app.services.crawler.parser import parse_articles


def crawl_source(
    think_tank_id: int
) -> int:
    """
    抓取单个智库来源
    """
    import asyncio

    return asyncio.run(
        _crawl_source_async(
            think_tank_id
        )
    )


async def _crawl_source_async(
    think_tank_id: int
) -> int:
    """
    异步执行：查询 Source 并抓取解析 HTML
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Source)
            .where(
                Source.think_tank_id == think_tank_id
            )
        )
        source = result.scalar_one_or_none()

        if not source:
            return 0

        html = await fetch_html(
            source.url
        )

        articles = parse_articles(
            html
        )

        print(
            f"{source.url}: {len(articles)} articles"
        )

        return len(articles)


async def _get_active_sources() -> list[dict]:
    """
    内部异步函数：仅用于安全获取激活的 Source 数据
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Source)
            .where(
                Source.is_active.is_(True)
            )
        )
        sources = result.scalars().all()

        return [
            {
                "think_tank_id": source.think_tank_id,
                "url": source.url
            }
            for source in sources
        ]


def crawl_all_sources() -> int:
    """
    抓取全部智库官网
    """
    import asyncio

    count = 0

    # 1. 异步获取所有需抓取的来源数据
    sources_data = asyncio.run(_get_active_sources())

    # 2. 同步环境中循环，为每个任务创建独立的 asyncio 事件循环，互不阻塞
    for source in sources_data:
        try:
            count += crawl_source(
                source["think_tank_id"]
            )
        except Exception as e:
            print(
                f"crawl failed {source['url']}: {e}"
            )

    return count
