import logging
from dataclasses import dataclass

from app.core.llm import SiliconFlowClient
from app.db.session import AsyncSessionLocal
from app.services.ai.report_ai_chunk_service import (
    claim_report_ai_chunk,
    complete_report_ai_chunk,
    fail_report_ai_chunk,
    generate_report_ai_chunk_output,
    load_report_ai_chunk_execution_input,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AIChunkRunResult:
    chunk_id: int
    status: str
    retry_count: int | None = None
    output_length: int | None = None
    error: str | None = None


async def run_report_ai_chunk(
    chunk_id: int,
) -> AIChunkRunResult:
    """
    独立执行一个报告 AI 分块。

    执行流程：

    1. 短数据库事务：
       claim -> processing
       读取并校验执行输入
       commit

    2. 关闭数据库 Session 后调用 AI。

    3. 再开启一个短数据库事务：
       success -> 保存 output_text
       failed  -> 保存错误并增加 retry_count

    本函数不负责 Celery 重试调度。
    """

    # ============================================================
    # 第一阶段：领取任务并准备脱离数据库使用的输入
    # ============================================================
    async with AsyncSessionLocal() as db:
        try:
            claimed = await claim_report_ai_chunk(
                db,
                chunk_id,
            )

            # processing / success 块不能重复执行。
            if claimed is None:
                await db.rollback()

                logger.info(
                    "AI chunk skipped: chunk_id=%s",
                    chunk_id,
                )

                return AIChunkRunResult(
                    chunk_id=chunk_id,
                    status="skipped",
                )

            execution_input = (
                await load_report_ai_chunk_execution_input(
                    db,
                    chunk_id,
                )
            )

            # 只有 claim 和输入校验都成功，
            # 才正式持久化 processing 状态。
            await db.commit()

        except Exception:
            await db.rollback()

            logger.exception(
                "Failed to claim/load AI chunk: "
                "chunk_id=%s",
                chunk_id,
            )

            raise

    # ============================================================
    # 第二阶段：数据库 Session 已关闭，只调用 AI
    # ============================================================
    try:
        async with SiliconFlowClient() as client:
            output_text = (
                await generate_report_ai_chunk_output(
                    client,
                    execution_input,
                )
            )

    except Exception as exc:
        logger.exception(
            "AI chunk generation failed: "
            "chunk_id=%s",
            chunk_id,
        )

        # ========================================================
        # 第三阶段 A：独立事务写入失败状态
        # ========================================================
        async with AsyncSessionLocal() as db:
            try:
                failed_chunk = (
                    await fail_report_ai_chunk(
                        db,
                        chunk_id,
                        exc,
                    )
                )

                retry_count = (
                    failed_chunk.retry_count
                )

                final_status = (
                    failed_chunk.status
                )

                await db.commit()

            except Exception:
                await db.rollback()

                logger.exception(
                    "Failed to persist AI chunk failure: "
                    "chunk_id=%s",
                    chunk_id,
                )

                raise

        # 如果出现迟到的失败结果，而数据库中的块
        # 已经成功，则不能把它报告成 failed。
        if final_status == "success":
            return AIChunkRunResult(
                chunk_id=chunk_id,
                status="skipped",
                retry_count=retry_count,
            )

        return AIChunkRunResult(
            chunk_id=chunk_id,
            status="failed",
            retry_count=retry_count,
            error=str(exc)[:2000],
        )

    # ============================================================
    # 第三阶段 B：独立事务写入成功结果
    # ============================================================
    async with AsyncSessionLocal() as db:
        try:
            completed_chunk = (
                await complete_report_ai_chunk(
                    db,
                    chunk_id,
                    output_text,
                )
            )

            retry_count = (
                completed_chunk.retry_count
            )

            await db.commit()

        except Exception:
            await db.rollback()

            logger.exception(
                "Failed to persist AI chunk success: "
                "chunk_id=%s",
                chunk_id,
            )

            raise

    logger.info(
        "AI chunk completed: chunk_id=%s, "
        "output_length=%s",
        chunk_id,
        len(output_text),
    )

    return AIChunkRunResult(
        chunk_id=chunk_id,
        status="success",
        retry_count=retry_count,
        output_length=len(output_text),
    )
