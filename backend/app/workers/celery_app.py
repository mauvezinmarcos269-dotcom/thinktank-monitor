from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# 初始化 Celery 实例
celery_app = Celery(
    "thinktank_monitor",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.models",
        "app.workers.tasks",
        "app.workers.crawl_tasks",
    ],
)

# Celery 全局配置
celery_app.conf.update(
    timezone="Asia/Shanghai",
    enable_utc=False,

    # 序列化配置
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # worker 优化参数
    worker_prefetch_multiplier=1,
    task_acks_late=True,

    # 定时任务配置
    beat_schedule={
        "daily-crawl": {
            "task": "crawl.all_think_tanks",
            "schedule": crontab(hour=2, minute=0),
        }
    },
)
