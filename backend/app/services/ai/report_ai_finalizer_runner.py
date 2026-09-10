from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.core.llm import SiliconFlowClient
from app.db.session import AsyncSessionLocal
from app.services.ai.report_ai_finalizer import (
    claim_report_ai_finalization,
    complete_report_ai_finalization,
    fail_report_ai_finalization,
    save_report_ai_partial_finalization,
)
from app.services.ai.report_ai_service import (
    generate_commentary_from_notes,
    generate_summary_from_notes,
)
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReportAIFinalizationRunResult:
    report_id: int
    status: str
    retry_count: int | None = None
    translation_length: int | None = None
    summary_length: int | None = None
    commentary_length: int | None = None
    error: str | None = None


@dataclass(frozen=True)
class FinalReportOutputResult:
    summary: str | None
    commentary: str | None
    errors: tuple[BaseException, ...] = ()


async def _generate_final_report_outputs(
    client: SiliconFlowClient,
    *,
    title: str,
    analysis_notes: str,
    existing_summary: str | None = None,
    existing_commentary: str | None = None,
) -> FinalReportOutputResult:
    """
    生成最终摘要和最终评论。

    已经成功保存过的字段会直接复用，只补齐缺失字段。
    使用 return_exceptions=True，确保两个请求都结束以后才退出
    client context，避免一个请求失败后另一个请求仍使用已关闭 client。
    """
    summary_result = existing_summary
    commentary_result = existing_commentary

    jobs = []

    if not summary_result:
        jobs.append(
            (
                "summary",
                generate_summary_from_notes(
                    client,
                    title,
                    analysis_notes,
                ),
            )
        )

    if not commentary_result:
        jobs.append(
            (
                "commentary",
                generate_commentary_from_notes(
                    client,
                    title,
                    analysis_notes,
                ),
            )
        )

    labels = [
        label
        for label, _ in jobs
    ]
    results = await asyncio.gather(
        *[
            job
            for _, job in jobs
        ],
        return_exceptions=True,
    )

    errors: list[BaseException] = []
    failed_labels: set[str] = set()

    for label, result in zip(
        labels,
        results,
        strict=True,
    ):
        if isinstance(
            result,
            BaseException,
        ):
            errors.append(result)
            failed_labels.add(label)
            continue

        if not isinstance(
            result,
            str,
        ):
            errors.append(
                ValueError(
                    f"最终{label}返回类型异常"
                )
            )
            failed_labels.add(label)
            continue

        if label == "summary":
            summary_result = result
        else:
            commentary_result = result

    if (
        not summary_result
        and "summary" not in failed_labels
    ):
        errors.append(
            ValueError("最终摘要为空")
        )

    if (
        not commentary_result
        and "commentary" not in failed_labels
    ):
        errors.append(
            ValueError("最终评论为空")
        )

    return FinalReportOutputResult(
        summary_result,
        commentary_result,
        tuple(errors),
    )


async def run_report_ai_finalization(
    report_id: int,
) -> ReportAIFinalizationRunResult:
    """
    执行整篇报告的最终 AI 收尾。

    第一阶段：
        短数据库事务 claim finalizing，
        合并 translation 和 analysis notes。

    第二阶段：
        关闭数据库 Session 后，
        并行生成 summary / commentary。

    第三阶段：
        新事务写入最终结果或失败状态。
    """

    # ============================================================
    # 第一阶段：claim + 准备脱离数据库的输入
    # ============================================================
    async with AsyncSessionLocal() as db:
        try:
            claim = (
                await claim_report_ai_finalization(
                    db,
                    report_id,
                )
            )

            if claim.status != "ready":
                await db.commit()

                return ReportAIFinalizationRunResult(
                    report_id=report_id,
                    status=claim.status,
                    error=claim.error,
                )

            if claim.execution_input is None:
                await db.rollback()

                raise RuntimeError(
                    "Finalization ready "
                    "但缺少 execution_input"
                )

            execution_input = (
                claim.execution_input
            )

            # finalizing 必须先落库，
            # 才能释放 DB 后调用模型。
            await db.commit()

        except Exception:
            await db.rollback()

            logger.exception(
                "Failed to claim report finalization: "
                "report_id=%s",
                report_id,
            )

            raise

    # ============================================================
    # 第二阶段：数据库已关闭，只调用 AI
    # ============================================================
    summary: str | None = None
    commentary: str | None = None

    try:
        async with SiliconFlowClient() as client:
            output_result = (
                await _generate_final_report_outputs(
                    client,
                    title=execution_input.title,
                    analysis_notes=(
                        execution_input.analysis_notes
                    ),
                    existing_summary=(
                        execution_input.summary
                    ),
                    existing_commentary=(
                        execution_input.commentary
                    ),
                )
            )

            summary = output_result.summary
            commentary = output_result.commentary

            if output_result.errors:
                first_error = output_result.errors[0]
                raise RuntimeError(
                    "报告最终摘要/评论生成失败: "
                    f"{type(first_error).__name__}: "
                    f"{first_error}"
                ) from first_error

    except Exception as exc:
        logger.exception(
            "Report finalization generation failed: "
            "report_id=%s",
            report_id,
        )

        # ========================================================
        # 第三阶段 A：finalizer 失败
        # ========================================================
        async with AsyncSessionLocal() as db:
            try:
                if summary or commentary:
                    failed_report = (
                        await save_report_ai_partial_finalization(
                            db,
                            report_id,
                            translation=(
                                execution_input.translation
                            ),
                            summary=summary,
                            commentary=commentary,
                            error=exc,
                        )
                    )
                else:
                    failed_report = (
                        await fail_report_ai_finalization(
                            db,
                            report_id,
                            exc,
                        )
                    )

                retry_count = (
                    failed_report.ai_retry_count
                )

                final_status = (
                    failed_report.ai_status
                )

                if final_status == "failed":
                    await notification_service.create_for_all_active_users(
                        db,
                        event_type="report.ai_failed",
                        title="报告 AI 处理失败",
                        message=f"{failed_report.title}: {str(exc)[:1000]}",
                        report_id=failed_report.id,
                    )

                await db.commit()

            except Exception:
                await db.rollback()

                logger.exception(
                    "Failed to persist report "
                    "finalization failure: "
                    "report_id=%s",
                    report_id,
                )

                raise

        if final_status == "success":
            return ReportAIFinalizationRunResult(
                report_id=report_id,
                status="skipped",
                retry_count=retry_count,
            )

        return ReportAIFinalizationRunResult(
            report_id=report_id,
            status="failed",
            retry_count=retry_count,
            translation_length=len(
                execution_input.translation
            ),
            summary_length=(
                len(summary)
                if summary
                else None
            ),
            commentary_length=(
                len(commentary)
                if commentary
                else None
            ),
            error=str(exc)[:2000],
        )

    # ============================================================
    # 第三阶段 B：一次性写入最终结果
    # ============================================================
    async with AsyncSessionLocal() as db:
        try:
            completed_report = (
                await complete_report_ai_finalization(
                    db,
                    report_id,
                    translation=(
                        execution_input.translation
                    ),
                    summary=summary or "",
                    commentary=commentary or "",
                )
            )

            retry_count = (
                completed_report.ai_retry_count
            )

            await notification_service.create_for_all_active_users(
                db,
                event_type="report.ai_completed",
                title="报告翻译与评论已完成",
                message=f"{completed_report.title}",
                report_id=completed_report.id,
            )

            await db.commit()

        except Exception:
            await db.rollback()

            logger.exception(
                "Failed to persist report "
                "finalization success: "
                "report_id=%s",
                report_id,
            )

            raise

    logger.info(
        "Report AI finalization completed: "
        "report_id=%s, "
        "translation_len=%s, "
        "summary_len=%s, "
        "commentary_len=%s",
        report_id,
        len(execution_input.translation),
        len(summary or ""),
        len(commentary or ""),
    )

    return ReportAIFinalizationRunResult(
        report_id=report_id,
        status="success",
        retry_count=retry_count,
        translation_length=len(
            execution_input.translation
        ),
        summary_length=len(summary or ""),
        commentary_length=len(commentary or ""),
    )
