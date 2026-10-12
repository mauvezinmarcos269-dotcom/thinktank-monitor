import asyncio

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.services.notification_service import notification_service
from app.workers.celery_app import celery_app


async def _create_daily_summary() -> dict[str, int | str]:
    async with AsyncSessionLocal() as db:
        return await notification_service.create_daily_summary(
            db,
            lookback_hours=settings.NOTIFICATION_SUMMARY_LOOKBACK_HOURS,
        )


@celery_app.task(name="notification.daily_summary")
def daily_summary_task() -> dict[str, int | str]:
    if not settings.NOTIFICATION_DAILY_SUMMARY_ENABLED:
        return {"status": "disabled"}

    return asyncio.run(_create_daily_summary())
