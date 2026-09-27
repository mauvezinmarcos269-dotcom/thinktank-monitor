from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.status import AIChunkStatus, AIChunkType, ReportAIStatus
from app.models.report import Report
from app.models.report_ai_chunk import ReportAIChunk
from app.utils.datetime import utc_now_naive

DEFAULT_MAX_CHUNK_RETRIES = 3
DEFAULT_MAX_FINALIZATION_RETRIES = 3


@dataclass(frozen=True)
class ReportAIFinalizationInput:
    report_id: int
    title: str
    translation: str
    analysis_notes: str
    summary: str | None = None
    commentary: str | None = None


@dataclass(frozen=True)
class ReportAIFinalizationClaim:
    status: str
    execution_input: ReportAIFinalizationInput | None = None
    error: str | None = None


@dataclass(frozen=True)
class ReportAIFinalizationQueueResult:
    report_id: int
    status: str
    error: str | None = None


def _validate_complete_chunk_group(
    chunks: list[ReportAIChunk],
    chunk_type: str,
) -> list[ReportAIChunk]:
    """
    校验同一类型的 chunk 是否完整。

    必须满足：
    1. 至少存在一个 chunk；
    2. chunk_count 一致；
    3. 实际数量等于 chunk_count；
    4. chunk_index 连续为 1..chunk_count。
    """
    group = [
        chunk
        for chunk in chunks
        if chunk.chunk_type == chunk_type
    ]

    group.sort(
        key=lambda chunk: chunk.chunk_index
    )

    if not group:
        raise ValueError(
            f"报告缺少 {chunk_type} chunks"
        )

    expected_count = group[0].chunk_count

    if expected_count <= 0:
        raise ValueError(
            f"{chunk_type} chunk_count 非法"
        )

    if any(
        chunk.chunk_count != expected_count
        for chunk in group
    ):
        raise ValueError(
            f"{chunk_type} chunk_count 不一致"
        )

    if len(group) != expected_count:
        raise ValueError(
            f"{chunk_type} chunks 数量不完整："
            f"expected={expected_count}, "
            f"actual={len(group)}"
        )

    expected_indices = list(
        range(
            1,
            expected_count + 1,
        )
    )

    actual_indices = [
        chunk.chunk_index
        for chunk in group
    ]

    if actual_indices != expected_indices:
        raise ValueError(
            f"{chunk_type} chunk_index 不连续："
            f"{actual_indices}"
        )

    return group


def _merge_translation_chunks(
    chunks: list[ReportAIChunk],
) -> str:
    """
    按 chunk_index 合并完整中文翻译。
    """
    group = _validate_complete_chunk_group(
        chunks,
        AIChunkType.translation.value,
    )

    translations: list[str] = []

    for chunk in group:
        if (
            chunk.status != AIChunkStatus.success.value
            or not chunk.output_text
        ):
            raise ValueError(
                "translation chunk 尚未全部成功"
            )

        translations.append(
            chunk.output_text
        )

    return "\n\n".join(translations)


def _merge_analysis_chunks(
    chunks: list[ReportAIChunk],
) -> str:
    """
    按原来的全文分析格式合并 analysis notes。
    """
    group = _validate_complete_chunk_group(
        chunks,
        AIChunkType.analysis.value,
    )

    notes: list[str] = []

    for chunk in group:
        if (
            chunk.status != AIChunkStatus.success.value
            or not chunk.output_text
        ):
            raise ValueError(
                "analysis chunk 尚未全部成功"
            )

        notes.append(
            f"【第 {chunk.chunk_index}/"
            f"{chunk.chunk_count} 部分分析笔记】\n"
            f"{chunk.output_text}"
        )

    return "\n\n".join(notes)


async def queue_report_ai_finalization(
    db: AsyncSession,
    report_id: int,
    *,
    max_chunk_retries: int = DEFAULT_MAX_CHUNK_RETRIES,
) -> ReportAIFinalizationQueueResult:
    """
    尝试预占整篇报告的 finalizer。

    processing / pending + 全部 chunk success:
        -> finalize_queued

    finalize_queued / finalizing / success / failed:
        不重复投递。

    若存在达到最大重试次数的 failed chunk:
        Report.ai_status -> failed。

    本函数只 flush，不 commit。
    """
    result = await db.execute(
        select(Report)
        .where(
            Report.id == report_id
        )
        .with_for_update()
    )

    report = result.scalar_one_or_none()

    if report is None:
        return ReportAIFinalizationQueueResult(
            report_id=report_id,
            status="not_found",
        )

    if report.ai_status in {
        ReportAIStatus.finalize_queued.value,
        ReportAIStatus.finalizing.value,
        ReportAIStatus.success.value,
        ReportAIStatus.failed.value,
    }:
        return ReportAIFinalizationQueueResult(
            report_id=report_id,
            status="skipped",
        )

    result = await db.execute(
        select(ReportAIChunk)
        .where(
            ReportAIChunk.report_id
            == report_id
        )
        .order_by(
            ReportAIChunk.chunk_type,
            ReportAIChunk.chunk_index,
        )
    )

    chunks = list(
        result.scalars().all()
    )

    if not chunks:
        return ReportAIFinalizationQueueResult(
            report_id=report_id,
            status="waiting",
        )

    exhausted_chunks = [
        chunk
        for chunk in chunks
        if (
            chunk.status == AIChunkStatus.failed.value
            and chunk.retry_count
            >= max_chunk_retries
        )
    ]

    if exhausted_chunks:
        report.ai_status = ReportAIStatus.failed.value
        report.updated_at = utc_now_naive()

        await db.flush()

        exhausted_ids = [
            chunk.id
            for chunk in exhausted_chunks
        ]

        return ReportAIFinalizationQueueResult(
            report_id=report_id,
            status="failed",
            error=(
                "AI chunks exceeded max retries: "
                f"{exhausted_ids}"
            ),
        )

    if any(
        chunk.status != AIChunkStatus.success.value
        for chunk in chunks
    ):
        return ReportAIFinalizationQueueResult(
            report_id=report_id,
            status="waiting",
        )

    # 所有 chunk 都是 success 后，再校验：
    # - translation 数量完整
    # - analysis 数量完整
    # - chunk_index 连续
    # - output_text 非空
    try:
        _merge_translation_chunks(
            chunks
        )

        _merge_analysis_chunks(
            chunks
        )

    except Exception as exc:
        report.ai_status = ReportAIStatus.failed.value
        report.updated_at = utc_now_naive()

        await db.flush()

        return ReportAIFinalizationQueueResult(
            report_id=report_id,
            status="failed",
            error=str(exc)[:2000],
        )

    report.ai_status = ReportAIStatus.finalize_queued.value
    report.updated_at = utc_now_naive()

    await db.flush()

    return ReportAIFinalizationQueueResult(
        report_id=report_id,
        status="queued",
    )


async def reset_queued_report_ai_finalization(
    db: AsyncSession,
    report_id: int,
) -> Report | None:
    """
    finalizer 的 Celery 投递失败时恢复报告状态。

    finalize_queued:
        -> processing

    其他状态：
        不处理，返回 None。

    不增加 ai_retry_count，
    因为最终摘要/评论尚未真正开始执行。

    本函数只 flush，不 commit。
    """
    result = await db.execute(
        select(Report)
        .where(
            Report.id == report_id
        )
        .with_for_update()
    )

    report = result.scalar_one_or_none()

    if report is None:
        raise ValueError(
            f"报告不存在：{report_id}"
        )

    if report.ai_status != ReportAIStatus.finalize_queued.value:
        return None

    report.ai_status = ReportAIStatus.processing.value
    report.updated_at = utc_now_naive()

    await db.flush()

    return report


async def recover_stale_report_ai_finalization(
    db: AsyncSession,
    report_id: int,
    *,
    finalize_queued_stale_before,
    finalizing_stale_before,
    max_finalization_retries: int = (
        DEFAULT_MAX_FINALIZATION_RETRIES
    ),
) -> Report | None:
    """
    恢复因 Worker 崩溃、容器重启或硬超时而遗留的
    report-level AI finalization 状态。

    stale finalize_queued:
        -> processing
        不增加 ai_retry_count，因为 finalizer 尚未确认开始。

    stale finalizing:
        ai_retry_count += 1

        未达到最大次数：
            -> processing

        达到最大次数：
            -> failed

    本函数只 flush，不 commit。
    """
    result = await db.execute(
        select(Report)
        .where(
            Report.id == report_id
        )
        .with_for_update()
    )

    report = result.scalar_one_or_none()

    if report is None:
        return None

    now = utc_now_naive()

    if report.ai_status == ReportAIStatus.finalize_queued.value:
        is_stale = (
            report.updated_at is None
            or report.updated_at
            < finalize_queued_stale_before
        )

        if not is_stale:
            return None

        report.ai_status = ReportAIStatus.processing.value
        report.updated_at = now

        await db.flush()

        return report

    if report.ai_status == ReportAIStatus.finalizing.value:
        is_stale = (
            report.updated_at is None
            or report.updated_at
            < finalizing_stale_before
        )

        if not is_stale:
            return None

        report.ai_retry_count = (
            report.ai_retry_count or 0
        ) + 1

        if (
            report.ai_retry_count
            >= max_finalization_retries
        ):
            report.ai_status = ReportAIStatus.failed.value
        else:
            report.ai_status = ReportAIStatus.processing.value

        report.updated_at = now

        await db.flush()

        return report

    return None


async def claim_report_ai_finalization(
    db: AsyncSession,
    report_id: int,
    *,
    max_chunk_retries: int = DEFAULT_MAX_CHUNK_RETRIES,
) -> ReportAIFinalizationClaim:
    """
    检查报告是否已经具备最终收尾条件。

    并发保护：
    使用 Report 行锁。

    finalize_queued 或已满足条件的 processing/pending:
        -> finalizing

    已经 finalizing / success:
        跳过。

    存在达到最大重试次数的 failed chunk:
        Report.ai_status -> failed。

    仍有普通 pending/queued/processing/retryable failed:
        返回 waiting。

    本函数只 flush，不 commit。
    """
    result = await db.execute(
        select(Report)
        .where(
            Report.id == report_id
        )
        .with_for_update()
    )

    report = result.scalar_one_or_none()

    if report is None:
        return ReportAIFinalizationClaim(
            status="not_found",
        )

    if report.ai_status == ReportAIStatus.success.value:
        return ReportAIFinalizationClaim(
            status="skipped",
        )

    if report.ai_status == ReportAIStatus.finalizing.value:
        return ReportAIFinalizationClaim(
            status="skipped",
        )

    result = await db.execute(
        select(ReportAIChunk)
        .where(
            ReportAIChunk.report_id
            == report_id
        )
        .order_by(
            ReportAIChunk.chunk_type,
            ReportAIChunk.chunk_index,
        )
    )

    chunks = list(
        result.scalars().all()
    )

    if not chunks:
        return ReportAIFinalizationClaim(
            status="waiting",
        )

    exhausted_chunks = [
        chunk
        for chunk in chunks
        if (
            chunk.status == AIChunkStatus.failed.value
            and chunk.retry_count
            >= max_chunk_retries
        )
    ]

    if exhausted_chunks:
        report.ai_status = ReportAIStatus.failed.value
        report.updated_at = utc_now_naive()

        await db.flush()

        exhausted_ids = [
            chunk.id
            for chunk in exhausted_chunks
        ]

        return ReportAIFinalizationClaim(
            status="failed",
            error=(
                "AI chunks exceeded max retries: "
                f"{exhausted_ids}"
            ),
        )

    # 只要还有一个 chunk 没成功，就不能最终合并。
    if any(
        chunk.status != AIChunkStatus.success.value
        for chunk in chunks
    ):
        return ReportAIFinalizationClaim(
            status="waiting",
        )

    # 所有状态 success 后，再严格验证两类 chunk
    # 是否数量完整、索引连续、output_text 非空。
    translation = _merge_translation_chunks(
        chunks
    )

    analysis_notes = _merge_analysis_chunks(
        chunks
    )

    # Report 行锁保证多个最后完成的 chunk
    # 同时尝试 finalization 时只有一个能 claim。
    report.ai_status = ReportAIStatus.finalizing.value
    report.updated_at = utc_now_naive()

    await db.flush()

    return ReportAIFinalizationClaim(
        status="ready",
        execution_input=(
            ReportAIFinalizationInput(
                report_id=report.id,
                title=(
                    report.title
                    or "未命名报告"
                ),
                translation=translation,
                analysis_notes=analysis_notes,
                summary=report.summary,
                commentary=report.commentary,
            )
        ),
    )


async def complete_report_ai_finalization(
    db: AsyncSession,
    report_id: int,
    *,
    translation: str,
    summary: str,
    commentary: str,
) -> Report:
    """
    完成整篇报告 AI 收尾。

    只有 finalizing 状态允许写入最终结果。

    本函数只 flush，不 commit。
    """
    if not translation:
        raise ValueError("最终翻译不能为空")

    if not summary:
        raise ValueError("最终摘要不能为空")

    if not commentary:
        raise ValueError("最终评论不能为空")

    result = await db.execute(
        select(Report)
        .where(
            Report.id == report_id
        )
        .with_for_update()
    )

    report = result.scalar_one_or_none()

    if report is None:
        raise ValueError(
            f"报告不存在：{report_id}"
        )

    # 已成功的报告不允许被迟到结果覆盖。
    if report.ai_status == ReportAIStatus.success.value:
        return report

    if report.ai_status != ReportAIStatus.finalizing.value:
        raise ValueError(
            "只有 finalizing 状态的报告 "
            "才能完成 AI 收尾，"
            f"当前状态：{report.ai_status}"
        )

    now = utc_now_naive()

    report.translation = translation
    report.summary = summary
    report.commentary = commentary

    report.ai_status = ReportAIStatus.success.value
    report.ai_retry_count = 0
    report.ai_generated_at = now
    report.updated_at = now

    await db.flush()

    return report


async def save_report_ai_partial_finalization(
    db: AsyncSession,
    report_id: int,
    *,
    translation: str,
    summary: str | None,
    commentary: str | None,
    error: Exception | str,
) -> Report:
    """
    保存 finalizer 已经生成合格的一部分结果，并标记本轮失败。

    后续手动重试时，claim 会把这些已合格字段带回执行输入，
    finalizer 只补齐缺失字段，避免成功结果被反复丢弃。
    """
    if not translation:
        raise ValueError("最终翻译不能为空")

    result = await db.execute(
        select(Report)
        .where(
            Report.id == report_id
        )
        .with_for_update()
    )

    report = result.scalar_one_or_none()

    if report is None:
        raise ValueError(
            f"报告不存在：{report_id}"
        )

    if report.ai_status == ReportAIStatus.success.value:
        return report

    if report.ai_status != ReportAIStatus.finalizing.value:
        raise ValueError(
            "只有 finalizing 状态的报告 "
            "才能保存 AI 部分收尾结果，"
            f"当前状态：{report.ai_status}"
        )

    now = utc_now_naive()

    report.translation = translation

    if summary:
        report.summary = summary

    if commentary:
        report.commentary = commentary

    report.ai_status = ReportAIStatus.failed.value
    report.ai_retry_count = (
        report.ai_retry_count or 0
    ) + 1
    report.updated_at = now

    await db.flush()

    return report


async def fail_report_ai_finalization(
    db: AsyncSession,
    report_id: int,
    error: Exception | str,
) -> Report:
    """
    将整篇报告 finalizer 标记为失败。

    注意：
    - 不修改任何 chunk；
    - 不清空已经成功的 chunk 输出；
    - 只增加 report.ai_retry_count；
    - 后续可直接重新运行 finalizer。

    本函数只 flush，不 commit。
    """
    result = await db.execute(
        select(Report)
        .where(
            Report.id == report_id
        )
        .with_for_update()
    )

    report = result.scalar_one_or_none()

    if report is None:
        raise ValueError(
            f"报告不存在：{report_id}"
        )

    # 迟到的失败结果不能覆盖 success。
    if report.ai_status == ReportAIStatus.success.value:
        return report

    if report.ai_status != ReportAIStatus.finalizing.value:
        raise ValueError(
            "只有 finalizing 状态的报告 "
            "才能标记 finalizer failed，"
            f"当前状态：{report.ai_status}"
        )

    report.ai_status = ReportAIStatus.failed.value

    report.ai_retry_count = (
        report.ai_retry_count or 0
    ) + 1

    report.updated_at = utc_now_naive()

    await db.flush()

    return report
