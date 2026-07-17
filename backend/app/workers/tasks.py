from .celery_app import celery_app


@celery_app.task(name="app.workers.tasks.test_task")
def test_task():
    """
    一个简单的测试任务，用于验证 Celery Worker 是否正常调度
    """
    return {
        "status": "success",
        "message": "Celery works perfectly!"
    }
