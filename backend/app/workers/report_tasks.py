import asyncio
import hashlib
import logging
from datetime import timedelta

from sqlalchemy import and_, func, or_, select

from app.db.session import AsyncSessionLocal
from app.models.report import Report
from app.models.report_ai_chunk import ReportAIChunk
from app.services.ai.report_ai_chunk_service import (
    prepare_report_ai_chunks,
    queue_report_ai_chunk,
    recover_stale_report_ai_chunk,
    reset_queued_report_ai_chunk,
)
from app.services.ai.report_ai_finalizer import (
    queue_report_ai_finalization,
    recover_stale_report_ai_finalization,
)
from app.services.crawler.report_document_service import (
    fetch_report_document,
)
from app.services.notification_service import notification_service
from app.utils.datetime import utc_now_naive
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
AI_CHUNK_MAX_RETRIES = 3
AI_CHUNK_QUEUED_STALE_MINUTES = 30

# chunk Celery task 的硬 time_limit 是 900 秒（15 分钟）。
# processing stale 阈值必须明显大于 15 分钟，
# 避免仍在正常运行的 AI 请求被误判为僵尸任务。
AI_CHUNK_PROCESSING_STALE_MINUTES = 20

# finalize_queued 正常情况下应很快被 Worker 消费。
# 10 分钟仍未进入 finalizing，允许重新投递。
AI_FINALIZE_QUEUED_STALE_MINUTES = 10

# finalizer Celery task hard time_limit = 900 秒（15 分钟）。
# 因此使用 20 分钟判断 finalizing 僵尸状态。
AI_FINALIZING_STALE_MINUTES = 20


# ==========================================
# Chunk AI 调度任务
# ==========================================
@celery_app.task(
    bind=True,
    name="report.enqueue_ai_chunk_tasks",
)
def enqueue_ai_chunk_tasks_task(
    self,
    report_limit: int = 10,
    chunk_limit: int = 50,
    only_report_id: int | None = None,
):
    """
    扫描可处理报告，准备 AI chunks，
    并投递 pending / 可重试 failed chunks。
    """
    logger.info(
        "Scheduler checking for AI chunk tasks..."
    )

    return asyncio.run(
        _enqueue_ai_chunk_tasks(
            report_limit=report_limit,
            chunk_limit=chunk_limit,
            only_report_id=only_report_id,
        )
    )


async def _enqueue_ai_chunk_tasks(
    report_limit: int,
    chunk_limit: int,
    only_report_id: int | None = None,
) -> list[int]:
    """
    准备并预占 AI chunks。

    数据库中先执行：

        pending / failed
        -> queued
        -> commit

    commit 成功后才投递 Celery。

    only_report_id 仅用于精确测试，
    正式定时调度时保持 None。
    """
    if report_limit <= 0:
        return []

    if chunk_limit <= 0:
        return []

    # 局部导入，避免 worker 模块之间循环引用。
    from app.workers.ai_tasks import (
        _dispatch_queued_report_ai_finalization,
        ai_chunk_task,
    )

    now = utc_now_naive()

    finalize_queued_stale_before = (
        now
        - timedelta(
            minutes=AI_FINALIZE_QUEUED_STALE_MINUTES
        )
    )

    finalizing_stale_before = (
        now
        - timedelta(
            minutes=AI_FINALIZING_STALE_MINUTES
        )
    )

    conditions = [
        Report.crawl_status == "success",
        Report.content.is_not(None),
        or_(
            Report.ai_status.in_(
                (
                    "pending",
                    "processing",
                    "failed",
                )
            ),
            and_(
                Report.ai_status
                == "finalize_queued",
                or_(
                    Report.updated_at.is_(None),
                    Report.updated_at
                    < finalize_queued_stale_before,
                ),
            ),
            and_(
                Report.ai_status
                == "finalizing",
                or_(
                    Report.updated_at.is_(None),
                    Report.updated_at
                    < finalizing_stale_before,
                ),
            ),
        ),
    ]

    if only_report_id is not None:
        conditions.append(
            Report.id == only_report_id
        )

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Report)
            .where(
                and_(*conditions)
            )
            .order_by(Report.id)
            .limit(report_limit)
            .with_for_update(
                skip_locked=True
            )
        )

        reports = list(
            result.scalars().all()
        )

        if not reports:
            return []

        queued_chunk_ids: list[int] = []
        queued_finalizer_report_ids: list[int] = []
        queued_stale_before = (
            now
            - timedelta(
                minutes=AI_CHUNK_QUEUED_STALE_MINUTES
            )
        )

        processing_stale_before = (
            now
            - timedelta(
                minutes=AI_CHUNK_PROCESSING_STALE_MINUTES
            )
        )

        for report in reports:
            recovered_report = (
                await recover_stale_report_ai_finalization(
                    db,
                    report.id,
                    finalize_queued_stale_before=(
                        finalize_queued_stale_before
                    ),
                    finalizing_stale_before=(
                        finalizing_stale_before
                    ),
                )
            )

            if recovered_report is not None:
                logger.warning(
                    "Recovered stale AI finalization: "
                    "report_id=%s, "
                    "status=%s, "
                    "retry_count=%s",
                    recovered_report.id,
                    recovered_report.ai_status,
                    recovered_report.ai_retry_count,
                )

                report = recovered_report

                # stale finalizing 已累计到最大失败次数，
                # 整篇报告到此终止，不再重新投递。
                if report.ai_status == "failed":
                    continue

            chunks = (
                await prepare_report_ai_chunks(
                    db,
                    report.id,
                )
            )

            report_has_queued_chunk = False

            for chunk in chunks:
                if (
                    len(queued_chunk_ids)
                    >= chunk_limit
                ):
                    break

                recovered = (
                    await recover_stale_report_ai_chunk(
                        db,
                        chunk.id,
                        queued_stale_before=(
                            queued_stale_before
                        ),
                        processing_stale_before=(
                            processing_stale_before
                        ),
                    )
                )

                if recovered is not None:
                    logger.warning(
                        "Recovered stale AI chunk: "
                        "chunk_id=%s, "
                        "status=%s, "
                        "retry_count=%s",
                        recovered.id,
                        recovered.status,
                        recovered.retry_count,
                    )

                    chunk = recovered

                if chunk.status == "success":
                    continue

                if chunk.status in {
                    "queued",
                    "processing",
                }:
                    continue

                if chunk.status == "failed":
                    if (
                        chunk.retry_count
                        >= AI_CHUNK_MAX_RETRIES
                    ):
                        continue

                if chunk.status != "pending":
                    if chunk.status != "failed":
                        continue

                queued = (
                    await queue_report_ai_chunk(
                        db,
                        chunk.id,
                    )
                )

                if queued is None:
                    continue

                queued_chunk_ids.append(
                    queued.id
                )

                report_has_queued_chunk = True

            if report_has_queued_chunk:
                report.ai_status = "processing"
                report.updated_at = now

            finalization_queue_result = (
                await queue_report_ai_finalization(
                    db,
                    report.id,
                )
            )

            if (
                finalization_queue_result.status
                == "queued"
            ):
                queued_finalizer_report_ids.append(
                    report.id
                )

            if (
                len(queued_chunk_ids)
                >= chunk_limit
            ):
                break

        # queued 必须先真正落库。
        await db.commit()

    successfully_enqueued_ids: list[int] = []

    # 数据库 commit 成功后再写入 Redis。
    for chunk_id in queued_chunk_ids:
        try:
            ai_chunk_task.delay(
                chunk_id
            )

            successfully_enqueued_ids.append(
                chunk_id
            )

        except Exception as exc:
            logger.exception(
                "Failed to enqueue AI chunk: "
                "chunk_id=%s",
                chunk_id,
            )

            # Celery 投递失败：
            # queued -> pending
            #
            # 使用独立事务恢复，避免这个 chunk
            # 永久卡在 queued。
            async with AsyncSessionLocal() as db:
                try:
                    recovered = (
                        await reset_queued_report_ai_chunk(
                            db,
                            chunk_id,
                            exc,
                        )
                    )

                    if recovered is not None:
                        report_id = (
                            recovered.report_id
                        )

                        # 如果这个报告已经没有任何
                        # queued / processing chunk，
                        # 则不能继续把整个报告留在
                        # processing。
                        result = await db.execute(
                            select(
                                func.count(
                                    ReportAIChunk.id
                                )
                            ).where(
                                and_(
                                    ReportAIChunk.report_id
                                    == report_id,
                                    ReportAIChunk.status.in_(
                                        (
                                            "queued",
                                            "processing",
                                        )
                                    ),
                                )
                            )
                        )

                        active_count = (
                            result.scalar_one()
                        )

                        if active_count == 0:
                            result = await db.execute(
                                select(Report)
                                .where(
                                    Report.id
                                    == report_id
                                )
                                .with_for_update()
                            )

                            report = (
                                result.scalar_one_or_none()
                            )

                            if (
                                report is not None
                                and report.ai_status
                                == "processing"
                            ):
                                report.ai_status = (
                                    "pending"
                                )

                                report.updated_at = (
                                    utc_now_naive()
                                )

                    await db.commit()

                except Exception:
                    await db.rollback()

                    logger.exception(
                        "Failed to recover AI chunk "
                        "after enqueue failure: "
                        "chunk_id=%s",
                        chunk_id,
                    )

                    raise

    for report_id in queued_finalizer_report_ids:
        finalization_status = (
            await _dispatch_queued_report_ai_finalization(
                report_id
            )
        )

        logger.info(
            "AI finalization scheduler dispatch: "
            "report_id=%s, status=%s",
            report_id,
            finalization_status,
        )

    logger.info(
        "Enqueued %s/%s AI chunks.",
        len(successfully_enqueued_ids),
        len(queued_chunk_ids),
    )

    return successfully_enqueued_ids


# ==========================================
# 1. 批量调度任务 (Beat 专用)
# ==========================================
@celery_app.task(
    bind=True,
    name="report.enqueue_pending_ai_tasks",
)
def enqueue_pending_ai_tasks_task(self, limit: int = 10):
    """
    旧任务名兼容入口。

    后端 AI 处理已统一走分块链路，避免再次启用
    旧的整篇报告一次性 AI 分析逻辑。
    """
    logger.info(
        "Legacy pending AI scheduler redirected to chunk scheduler."
    )
    return asyncio.run(
        _enqueue_pending_ai_tasks(limit)
    )


async def _enqueue_pending_ai_tasks(
    limit: int,
):
    """
    旧函数名兼容入口，内部统一转发到新分块调度器。
    """
    return await _enqueue_ai_chunk_tasks(
        report_limit=limit,
        chunk_limit=50,
    )


# ==========================================
# 2. 爬虫抓取内容任务 (保持不变)
# ==========================================
@celery_app.task(
    bind=True,
    name="report.fetch_content",
    time_limit=900,
)
def fetch_report_content_task(
    self,
    report_id: int,
) -> dict[str, int | str]:
    """
    Celery 报告正文抓取任务。
    """
    logger.info(
        "Celery manual crawl task started: report_id=%s, task_id=%s",
        report_id,
        self.request.id,
    )
    return _run_fetch_report_content(report_id)


def _run_fetch_report_content(
    report_id: int,
) -> dict[str, int | str]:
    """
    在 Celery 同步任务中运行异步抓取逻辑。
    """
    return asyncio.run(
        _fetch_report_content_async(report_id)
    )


async def _fetch_report_content_async(
    report_id: int,
) -> dict[str, int | str]:
    """
    抓取报告详情页、提取正文并更新数据库。
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Report).where(Report.id == report_id)
        )
        report = result.scalar_one_or_none()

        if report is None:
            logger.warning(
                "Manual crawl failed: report %s does not exist",
                report_id,
            )
            return {
                "status": "not_found",
                "report_id": report_id,
            }

        if report.crawl_status == "running":
            logger.info(
                "Report %s is already being crawled",
                report_id,
            )
            return {
                "status": "already_running",
                "report_id": report_id,
                "error": "Report is already being crawled",
            }

        # 先将状态设置为运行中，同时也更新 updated_at
        report.crawl_status = "running"
        report.crawl_error = None
        report.updated_at = utc_now_naive()
        await db.commit()

        try:
            document = await fetch_report_document(
                report.url
            )
            content = document.text

            logger.info(
                "Fetched report PDF: report_id=%s, "
                "page_url=%s, pdf_url=%s, "
                "page_count=%s, non_empty_pages=%s, "
                "pdf_bytes=%s, content_length=%s",
                report_id,
                document.page_url,
                document.pdf_url,
                document.page_count,
                document.non_empty_page_count,
                document.pdf_byte_length,
                len(content),
            )

            # 对清洗后的正文计算 SHA-256
            content_hash = hashlib.sha256(
                content.encode("utf-8")
            ).hexdigest()

            # 抓取成功，统一获取当前时间
            now = utc_now_naive()

            report.content = content
            report.content_hash = content_hash
            report.pdf_url = document.pdf_url
            report.page_count = document.page_count
            report.non_empty_page_count = document.non_empty_page_count
            report.pdf_byte_length = document.pdf_byte_length
            report.crawl_status = "success"
            report.crawl_error = None
            report.content_fetched_at = now
            report.updated_at = now
            report.translation = None
            report.summary = None
            report.commentary = None
            report.ai_status = "pending"
            report.ai_retry_count = 0
            report.ai_generated_at = None

            await db.commit()

            logger.info(
                "Manual crawl succeeded: report_id=%s, "
                "content_length=%s, content_hash=%s",
                report_id,
                len(content),
                content_hash,
            )

            return {
                "status": "success",
                "report_id": report.id,
                "content_length": len(content),
                "content_hash": content_hash,
            }

        except Exception as exc:
            logger.exception(
                "Manual crawl failed for report %s",
                report_id,
            )
            # 如果上一次数据库操作失败，必须先回滚事务
            await db.rollback()

            # 重新查询，避免使用处于异常事务状态中的对象
            result = await db.execute(
                select(Report).where(Report.id == report_id)
            )
            failed_report = result.scalar_one_or_none()
            if failed_report is not None:
                failed_report.crawl_status = "failed"
                failed_report.crawl_error = str(exc)[:2000]
                failed_report.updated_at = utc_now_naive()
                await notification_service.create_for_all_active_users(
                    db,
                    event_type="report.fetch_failed",
                    title="报告正文抓取失败",
                    message=f"{failed_report.title}: {failed_report.crawl_error}",
                    report_id=failed_report.id,
                )
                await db.commit()

            return {
                "status": "failed",
                "report_id": report_id,
                "error": str(exc),
            }
