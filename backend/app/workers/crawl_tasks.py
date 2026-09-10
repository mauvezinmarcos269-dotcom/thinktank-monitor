from .celery_app import celery_app


@celery_app.task(
    name="crawl.source",
    time_limit=600,
)
def crawl_source_task(source_id: int) -> dict[str, int | str]:
    """抓取单个来源。"""
    from app.services.crawler_service import crawl_source

    return crawl_source(source_id)


@celery_app.task(
    name="crawl.all_sources",
    time_limit=3600,
)
def crawl_all_sources_task() -> dict[str, int | str]:
    """定时抓取全部启用且已到抓取时间的来源。"""
    from app.services.crawler_service import crawl_all_sources

    saved_count = crawl_all_sources()

    return {
        "status": "success",
        "saved_count": saved_count,
    }
