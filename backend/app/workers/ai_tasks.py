import asyncio
import logging
from dataclasses import asdict

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.report_ai_chunk import ReportAIChunk
from app.services.ai.report_ai_chunk_runner import (
    run_report_ai_chunk,
)
from app.services.ai.report_ai_finalizer import (
    queue_report_ai_finalization,
    reset_queued_report_ai_finalization,
)
from app.services.ai.report_ai_finalizer_runner import (
    run_report_ai_finalization,
)
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
AI_FINALIZATION_MAX_RETRIES = 3
AI_FINALIZATION_RETRY_COUNTDOWN_SECONDS = 60


@celery_app.task(
    bind=True,
    name="report.ai_chunk",
    time_limit=900,
)
def ai_chunk_task(
    self,
    chunk_id: int,
) -> dict:
    """
    独立执行一个报告 AI 分块。

    重试策略暂时由数据库 chunk 状态控制，
    本 Celery task 暂不调用 self.retry()。
    """
    logger.info(
        "AI chunk task started: "
        "chunk_id=%s, task_id=%s",
        chunk_id,
        self.request.id,
    )

    result = asyncio.run(
        run_report_ai_chunk(
            chunk_id
        )
    )

    finalization_status = asyncio.run(
        _maybe_enqueue_report_ai_finalization(
            chunk_id
        )
    )

    logger.info(
        "AI chunk post-check: "
        "chunk_id=%s, "
        "chunk_status=%s, "
        "finalization_status=%s",
        chunk_id,
        result.status,
        finalization_status,
    )

    return asdict(result)


async def _dispatch_queued_report_ai_finalization(
    report_id: int,
    *,
    trigger_chunk_id: int | None = None,
) -> str:
    """
    投递一个已经持久化为 finalize_queued 的报告。

    Celery 投递成功：
        保持 finalize_queued。

    Celery 投递失败：
        finalize_queued -> processing。

    不增加 ai_retry_count，
    因为 finalizer 尚未真正执行。
    """
    try:
        ai_finalize_task.delay(
            report_id
        )

    except Exception:
        logger.exception(
            "Failed to enqueue AI finalization: "
            "report_id=%s, trigger_chunk_id=%s",
            report_id,
            trigger_chunk_id,
        )

        async with AsyncSessionLocal() as db:
            try:
                await reset_queued_report_ai_finalization(
                    db,
                    report_id,
                )

                await db.commit()

            except Exception:
                await db.rollback()

                logger.exception(
                    "Failed to recover report after "
                    "finalization enqueue failure: "
                    "report_id=%s",
                    report_id,
                )

                raise

        return "enqueue_failed"

    logger.info(
        "AI finalization enqueued: "
        "report_id=%s, trigger_chunk_id=%s",
        report_id,
        trigger_chunk_id,
    )

    return "queued"


async def _maybe_enqueue_report_ai_finalization(
    chunk_id: int,
) -> str:
    """
    chunk 执行结束后检查整篇报告是否已经可以进入 finalizer。

    多个 chunk 同时完成时，
    Report 行锁保证只有一个任务能：
        processing -> finalize_queued

    只有获得 queued 的调用才真正发送 Celery finalizer。
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ReportAIChunk).where(
                ReportAIChunk.id == chunk_id
            )
        )

        chunk = result.scalar_one_or_none()

        if chunk is None:
            return "not_found"

        report_id = chunk.report_id

        queue_result = (
            await queue_report_ai_finalization(
                db,
                report_id,
            )
        )

        # finalize_queued 必须先落数据库。
        await db.commit()

    if queue_result.status != "queued":
        return queue_result.status

    return await _dispatch_queued_report_ai_finalization(
        report_id,
        trigger_chunk_id=chunk_id,
    )


@celery_app.task(
    bind=True,
    name="report.ai_finalize",
    time_limit=900,
)
def ai_finalize_task(
    self,
    report_id: int,
) -> dict:
    """
    执行整篇报告的最终 AI 收尾。

    如果 summary/commentary 生成失败，
    只重试 finalizer，不重新执行任何 chunk。
    """
    logger.info(
        "AI finalization task started: "
        "report_id=%s, task_id=%s",
        report_id,
        self.request.id,
    )

    result = asyncio.run(
        run_report_ai_finalization(
            report_id
        )
    )

    # retry_count 为 None 的 failed，
    # 代表 chunk 已达到最大重试次数等
    # 非 finalizer-generation 失败，
    # 此时不应该重试 finalizer。
    if (
        result.status == "failed"
        and result.retry_count is not None
        and result.retry_count
        < AI_FINALIZATION_MAX_RETRIES
    ):
        logger.warning(
            "AI finalization will retry: "
            "report_id=%s, retry_count=%s",
            report_id,
            result.retry_count,
        )

        raise self.retry(
            exc=RuntimeError(
                result.error
                or "AI finalization failed"
            ),
            countdown=(
                AI_FINALIZATION_RETRY_COUNTDOWN_SECONDS
            ),
            max_retries=(
                AI_FINALIZATION_MAX_RETRIES - 1
            ),
        )

    return asdict(result)


# ==========================================
# 旧整篇 AI 分析任务兼容入口
# ==========================================
@celery_app.task(
    bind=True,
    name="report.ai_analysis",
)
def ai_analysis_task(
    self,
    report_id: int,
    lock_token: str | None = None,
):
    logger.info(
        "Legacy AI analysis task redirected to chunk scheduler: "
        "report=%s task=%s",
        report_id,
        self.request.id
    )
    return asyncio.run(
        _run_ai_analysis(
            report_id,
            lock_token,
        )
    )


async def _run_ai_analysis(
    report_id: int,
    lock_token: str | None = None,
):
    """
    旧函数名兼容入口。

    lock_token 仅为兼容历史 Celery 消息签名保留，
    后端 AI 生产路径统一使用分块调度器。
    """
    _ = lock_token

    from app.workers.report_tasks import _enqueue_ai_chunk_tasks

    chunk_ids = await _enqueue_ai_chunk_tasks(
        report_limit=1,
        chunk_limit=50,
        only_report_id=report_id,
    )

    return {
        "status": "queued" if chunk_ids else "skipped",
        "report_id": report_id,
        "chunk_ids": chunk_ids,
    }
