from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# 初始化 Celery 实例
celery_app = Celery(
    "thinktank_monitor",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.models",
        "app.workers.tasks",
        "app.workers.crawl_tasks",
        "app.workers.report_tasks",
        "app.workers.ai_tasks",
        "app.workers.notification_tasks",
    ],
)

# Celery 全局配置
celery_app.conf.update(
    timezone="Asia/Shanghai",  # 明确设为东八区
    enable_utc=False,          # 禁用纯 UTC 模式
    task_default_queue=settings.CELERY_TASK_DEFAULT_QUEUE,

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
            "task": "crawl.all_sources",
            "schedule": crontab(hour=18, minute=0),
        },
        # 新增：每 5 分钟轮询一次 pending 状态的报告投递给 AI
        "auto-enqueue-ai-tasks": {
            "task": "report.enqueue_ai_chunk_tasks",
            "schedule": crontab(minute="*/5"),
            "args": (10, 50),
        },
        "daily-notification-summary": {
            "task": "notification.daily_summary",
            "schedule": crontab(hour=19, minute=0),
        },
    },
)
