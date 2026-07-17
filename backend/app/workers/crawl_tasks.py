from .celery_app import celery_app


@celery_app.task(
    name="crawl.think_tank_website"
)
def crawl_think_tank_website(
    think_tank_id: int
):
    """
    抓取智库官网文章
    """
    from app.services.crawler_service import crawl_source

    result = crawl_source(
        think_tank_id
    )

    return {
        "status": "success",
        "count": result
    }


@celery_app.task(
    name="crawl.all_think_tanks",
    time_limit=3600
)
def crawl_all_think_tanks():
    """
    定时任务：抓取所有智库来源
    """
    from app.services.crawler_service import crawl_all_sources

    count = crawl_all_sources()

    return {
        "status": "success",
        "count": count
    }
