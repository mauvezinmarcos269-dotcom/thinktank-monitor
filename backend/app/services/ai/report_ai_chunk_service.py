from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import SiliconFlowClient
from app.core.status import AIChunkStatus, AIChunkType
from app.models.report import Report
from app.models.report_ai_chunk import ReportAIChunk
from app.schemas.ai_report import (
    AIChunkProgressRead,
    AIChunkTypeProgressRead,
    AIProgressRead,
)
from app.services.ai.report_ai_service import (
    _split_analysis_chunks,
    _split_text_into_chunks,
    generate_analysis_notes,
    generate_translation,
)
from app.utils.datetime import utc_now_naive


@dataclass(frozen=True)
class AIChunkSpec:
    chunk_type: str
    chunk_index: int
    chunk_count: int
    source_start: int
    source_end: int


@dataclass(frozen=True)
class AIChunkExecutionInput:
    chunk_id: int
    report_id: int
    chunk_type: str
    chunk_index: int
    chunk_count: int
    report_title: str
    content: str


def _build_chunk_specs(
    content: str,
    *,
    chunk_type: str,
    chunks: list[str],
) -> list[AIChunkSpec]:
    """
    根据已经切好的文本块生成字符区间。

    由于现有分块函数已经保证：
        "".join(chunks) == content

    因此可以通过累计长度得到精确 source_start/source_end，
    不需要再次搜索正文。
    """
    if not content:
        return []

    if "".join(chunks) != content:
        raise ValueError(
            f"{chunk_type} 分块无法还原原始正文"
        )

    specs: list[AIChunkSpec] = []

    chunk_count = len(chunks)
    cursor = 0

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):
        source_start = cursor
        source_end = source_start + len(chunk)

        specs.append(
            AIChunkSpec(
                chunk_type=chunk_type,
                chunk_index=index,
                chunk_count=chunk_count,
                source_start=source_start,
                source_end=source_end,
            )
        )

        cursor = source_end

    if cursor != len(content):
        raise ValueError(
            f"{chunk_type} 分块区间未覆盖完整正文"
        )

    return specs


def build_report_ai_chunk_specs(
    content: str,
) -> list[AIChunkSpec]:
    """
    为一篇完整报告生成两类 AI 分块计划：

    translation：
        使用全文翻译分块规则。

    analysis：
        使用全文分析笔记分块规则。
    """
    if not content:
        raise ValueError("报告正文不能为空")

    translation_chunks = (
        _split_text_into_chunks(
            content
        )
    )

    analysis_chunks = (
        _split_analysis_chunks(
            content
        )
    )

    translation_specs = _build_chunk_specs(
        content,
        chunk_type=AIChunkType.translation.value,
        chunks=translation_chunks,
    )

    analysis_specs = _build_chunk_specs(
        content,
        chunk_type=AIChunkType.analysis.value,
        chunks=analysis_chunks,
    )

    return (
        translation_specs
        + analysis_specs
    )


async def prepare_report_ai_chunks(
    db: AsyncSession,
    report_id: int,
) -> list[ReportAIChunk]:
    """
    为报告准备 translation / analysis 两类分块记录。

    特性：
    1. 相同正文、相同分块规则下可重复调用，不重复插入；
    2. 已成功的合法分块不会被覆盖；
    3. 如果正文 hash 或分块边界发生变化，则旧分块整体失效并重建；
    4. 本函数只 flush，不 commit，由调用方控制事务。
    """
    result = await db.execute(
        select(Report).where(
            Report.id == report_id
        )
    )
    report = result.scalar_one_or_none()

    if report is None:
        raise ValueError(
            f"报告不存在：{report_id}"
        )

    if not report.content:
        raise ValueError(
            f"报告正文为空：{report_id}"
        )

    content_hash = (
        report.content_hash
        or hashlib.sha256(
            report.content.encode("utf-8")
        ).hexdigest()
    )

    specs = build_report_ai_chunk_specs(
        report.content
    )

    expected_by_key = {
        (
            spec.chunk_type,
            spec.chunk_index,
        ): spec
        for spec in specs
    }

    result = await db.execute(
        select(ReportAIChunk).where(
            ReportAIChunk.report_id
            == report_id
        )
    )
    existing_chunks = list(
        result.scalars().all()
    )

    # 如果正文已变化，或已有记录的分块边界与
    # 当前算法不一致，则旧输出不能继续复用。
    requires_reset = False

    for chunk in existing_chunks:
        key = (
            chunk.chunk_type,
            chunk.chunk_index,
        )

        spec = expected_by_key.get(key)

        if spec is None:
            requires_reset = True
            break

        if (
            chunk.report_content_hash
            != content_hash
            or chunk.chunk_count
            != spec.chunk_count
            or chunk.source_start
            != spec.source_start
            or chunk.source_end
            != spec.source_end
        ):
            requires_reset = True
            break

    if requires_reset:
        await db.execute(
            delete(ReportAIChunk).where(
                ReportAIChunk.report_id
                == report_id
            )
        )

        # 明确先执行 DELETE，避免后续 INSERT
        # 与唯一约束产生冲突。
        await db.flush()

        existing_chunks = []

    existing_by_key = {
        (
            chunk.chunk_type,
            chunk.chunk_index,
        ): chunk
        for chunk in existing_chunks
    }

    for spec in specs:
        key = (
            spec.chunk_type,
            spec.chunk_index,
        )

        if key in existing_by_key:
            continue

        chunk = ReportAIChunk(
            report_id=report_id,
            chunk_type=spec.chunk_type,
            chunk_index=spec.chunk_index,
            chunk_count=spec.chunk_count,
            source_start=spec.source_start,
            source_end=spec.source_end,
            report_content_hash=content_hash,
            output_text=None,
            status=AIChunkStatus.pending.value,
            retry_count=0,
            last_error=None,
        )

        db.add(chunk)

    await db.flush()

    result = await db.execute(
        select(ReportAIChunk).where(
            ReportAIChunk.report_id
            == report_id
        )
    )

    chunks = list(
        result.scalars().all()
    )

    type_order = {
        AIChunkType.translation.value: 0,
        AIChunkType.analysis.value: 1,
    }

    chunks.sort(
        key=lambda chunk: (
            type_order.get(
                chunk.chunk_type,
                99,
            ),
            chunk.chunk_index,
        )
    )

    return chunks


async def get_report_ai_progress(
    db: AsyncSession,
    report_id: int,
) -> AIProgressRead | None:
    result = await db.execute(
        select(Report).where(
            Report.id == report_id
        )
    )
    report = result.scalar_one_or_none()

    if report is None:
        return None

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
    chunks = list(result.scalars().all())

    statuses = (
        AIChunkStatus.pending.value,
        AIChunkStatus.queued.value,
        AIChunkStatus.processing.value,
        AIChunkStatus.success.value,
        AIChunkStatus.failed.value,
    )
    by_type_map: dict[str, dict[str, int | str]] = {}

    for chunk in chunks:
        stats = by_type_map.setdefault(
            chunk.chunk_type,
            {
                "chunk_type": chunk.chunk_type,
                "total": 0,
                "pending": 0,
                "queued": 0,
                "processing": 0,
                "success": 0,
                "failed": 0,
            },
        )
        stats["total"] = int(stats["total"]) + 1

        if chunk.status in statuses:
            stats[chunk.status] = (
                int(stats[chunk.status]) + 1
            )

    latest_error = next(
        (
            chunk.last_error
            for chunk in sorted(
                chunks,
                key=lambda item: item.updated_at,
                reverse=True,
            )
            if chunk.last_error
        ),
        None,
    )

    running_chunks = sum(
        1
        for chunk in chunks
        if chunk.status
        in {
            AIChunkStatus.queued.value,
            AIChunkStatus.processing.value,
        }
    )

    return AIProgressRead(
        report_id=report.id,
        ai_status=report.ai_status,
        ai_retry_count=report.ai_retry_count or 0,
        ai_generated_at=report.ai_generated_at,
        total_chunks=len(chunks),
        completed_chunks=sum(
            1
            for chunk in chunks
            if chunk.status == AIChunkStatus.success.value
        ),
        failed_chunks=sum(
            1
            for chunk in chunks
            if chunk.status == AIChunkStatus.failed.value
        ),
        running_chunks=running_chunks,
        latest_error=latest_error,
        by_type=[
            AIChunkTypeProgressRead(
                **stats
            )
            for stats in by_type_map.values()
        ],
        chunks=[
            AIChunkProgressRead.model_validate(
                chunk
            )
            for chunk in chunks
        ],
    )


async def load_report_ai_chunk_execution_input(
    db: AsyncSession,
    chunk_id: int,
) -> AIChunkExecutionInput:
    """
    读取并校验一个已经领取的 AI 分块，
    返回可以脱离数据库 Session 使用的执行输入。

    本函数不调用模型，也不修改数据库。
    """
    result = await db.execute(
        select(ReportAIChunk).where(
            ReportAIChunk.id == chunk_id
        )
    )
    chunk = result.scalar_one_or_none()

    if chunk is None:
        raise ValueError(
            f"AI 分块不存在：{chunk_id}"
        )

    if chunk.status != AIChunkStatus.processing.value:
        raise ValueError(
            "只有 processing 状态的分块 "
            "才能生成 AI 输出，"
            f"当前状态：{chunk.status}"
        )

    result = await db.execute(
        select(Report).where(
            Report.id == chunk.report_id
        )
    )
    report = result.scalar_one_or_none()

    if report is None:
        raise ValueError(
            f"报告不存在：{chunk.report_id}"
        )

    if not report.content:
        raise ValueError(
            f"报告正文为空：{report.id}"
        )

    current_content_hash = (
        report.content_hash
        or hashlib.sha256(
            report.content.encode("utf-8")
        ).hexdigest()
    )

    if (
        current_content_hash
        != chunk.report_content_hash
    ):
        raise ValueError(
            "报告正文已变化，当前 AI 分块已经失效"
        )

    if not (
        0
        <= chunk.source_start
        < chunk.source_end
        <= len(report.content)
    ):
        raise ValueError(
            "AI 分块字符区间非法："
            f"{chunk.source_start}:"
            f"{chunk.source_end}, "
            f"content_len={len(report.content)}"
        )

    chunk_content = report.content[
        chunk.source_start:
        chunk.source_end
    ]

    return AIChunkExecutionInput(
        chunk_id=chunk.id,
        report_id=report.id,
        chunk_type=chunk.chunk_type,
        chunk_index=chunk.chunk_index,
        chunk_count=chunk.chunk_count,
        report_title=report.title,
        content=chunk_content,
    )


async def generate_report_ai_chunk_output(
    client: SiliconFlowClient,
    execution_input: AIChunkExecutionInput,
) -> str:
    """
    根据已经准备好的分块输入调用 AI。

    本函数完全不访问数据库。
    """
    if (
        execution_input.chunk_type
        == AIChunkType.translation.value
    ):
        chunk_title = (
            f"{execution_input.report_title} "
            f"（第 "
            f"{execution_input.chunk_index}/"
            f"{execution_input.chunk_count} "
            f"部分）"
        )

        return await generate_translation(
            client,
            chunk_title,
            execution_input.content,
        )

    if (
        execution_input.chunk_type
        == AIChunkType.analysis.value
    ):
        return await generate_analysis_notes(
            client,
            execution_input.report_title,
            execution_input.content,
            execution_input.chunk_index,
            execution_input.chunk_count,
        )

    raise ValueError(
        "不支持的 AI 分块类型："
        f"{execution_input.chunk_type}"
    )


async def queue_report_ai_chunk(
    db: AsyncSession,
    chunk_id: int,
) -> ReportAIChunk | None:
    """
    尝试把一个 AI 分块预占为 queued。

    pending / failed:
        可以进入 queued。

    queued / processing / success:
        不重复调度，返回 None。

    本函数只 flush，不 commit。
    """
    result = await db.execute(
        select(ReportAIChunk)
        .where(
            ReportAIChunk.id == chunk_id
        )
        .with_for_update()
    )

    chunk = result.scalar_one_or_none()

    if chunk is None:
        raise ValueError(
            f"AI 分块不存在：{chunk_id}"
        )

    if chunk.status in {
        AIChunkStatus.queued.value,
        AIChunkStatus.processing.value,
        AIChunkStatus.success.value,
    }:
        return None

    if chunk.status not in {
        AIChunkStatus.pending.value,
        AIChunkStatus.failed.value,
    }:
        raise ValueError(
            "不支持的 AI 分块状态："
            f"{chunk.status}"
        )

    chunk.status = AIChunkStatus.queued.value
    chunk.last_error = None
    chunk.updated_at = utc_now_naive()

    await db.flush()

    return chunk


async def reset_queued_report_ai_chunk(
    db: AsyncSession,
    chunk_id: int,
    error: Exception | str,
) -> ReportAIChunk | None:
    """
    Celery 投递失败时，将 queued 分块恢复为 pending。

    queued:
        -> pending

    如果状态已经被 Worker 改成 processing / success，
    说明任务可能实际上已经成功进入队列，
    此时不回退，返回 None。

    retry_count 不增加，因为 AI 实际上还没有执行。
    """
    result = await db.execute(
        select(ReportAIChunk)
        .where(
            ReportAIChunk.id == chunk_id
        )
        .with_for_update()
    )

    chunk = result.scalar_one_or_none()

    if chunk is None:
        raise ValueError(
            f"AI 分块不存在：{chunk_id}"
        )

    if chunk.status != AIChunkStatus.queued.value:
        return None

    chunk.status = AIChunkStatus.pending.value
    chunk.last_error = (
        "Celery enqueue failed: "
        f"{str(error)[:1900]}"
    )
    chunk.updated_at = utc_now_naive()

    await db.flush()

    return chunk


async def recover_stale_report_ai_chunk(
    db: AsyncSession,
    chunk_id: int,
    *,
    queued_stale_before: datetime,
    processing_stale_before: datetime,
) -> ReportAIChunk | None:
    """
    恢复超时的 AI 分块。

    queued 超时：
        queued -> pending
        不增加 retry_count，因为 AI 尚未真正执行。

    processing 超时：
        processing -> failed
        retry_count + 1，因为任务已经开始执行，
        但未能正常写回结果。

    其他状态或尚未超时：
        不处理，返回 None。

    本函数只 flush，不 commit。
    """
    result = await db.execute(
        select(ReportAIChunk)
        .where(
            ReportAIChunk.id == chunk_id
        )
        .with_for_update()
    )

    chunk = result.scalar_one_or_none()

    if chunk is None:
        raise ValueError(
            f"AI 分块不存在：{chunk_id}"
        )

    now = utc_now_naive()

    if (
        chunk.status == AIChunkStatus.queued.value
        and chunk.updated_at
        < queued_stale_before
    ):
        chunk.status = AIChunkStatus.pending.value

        chunk.last_error = (
            "Stale queued AI chunk recovered"
        )

        chunk.updated_at = now

        await db.flush()

        return chunk

    if (
        chunk.status == AIChunkStatus.processing.value
        and chunk.updated_at
        < processing_stale_before
    ):
        chunk.status = AIChunkStatus.failed.value

        chunk.retry_count = (
            chunk.retry_count or 0
        ) + 1

        chunk.last_error = (
            "Stale processing AI chunk recovered"
        )

        chunk.updated_at = now

        await db.flush()

        return chunk

    return None


async def claim_report_ai_chunk(
    db: AsyncSession,
    chunk_id: int,
) -> ReportAIChunk | None:
    """
    尝试领取一个 AI 分块。

    pending / failed / queued:
        可以领取，状态改为 processing。

    processing / success:
        不重复领取，返回 None。

    本函数只 flush，不 commit。
    """
    result = await db.execute(
        select(ReportAIChunk)
        .where(
            ReportAIChunk.id == chunk_id
        )
        .with_for_update()
    )

    chunk = result.scalar_one_or_none()

    if chunk is None:
        raise ValueError(
            f"AI 分块不存在：{chunk_id}"
        )

    if chunk.status in {
        AIChunkStatus.processing.value,
        AIChunkStatus.success.value,
    }:
        return None

    if chunk.status not in {
        AIChunkStatus.pending.value,
        AIChunkStatus.failed.value,
        AIChunkStatus.queued.value,
    }:
        raise ValueError(
            "不支持的 AI 分块状态："
            f"{chunk.status}"
        )

    chunk.status = AIChunkStatus.processing.value
    chunk.last_error = None
    chunk.updated_at = utc_now_naive()

    await db.flush()

    return chunk


async def complete_report_ai_chunk(
    db: AsyncSession,
    chunk_id: int,
    output_text: str,
) -> ReportAIChunk:
    """
    将一个 processing 分块标记为成功。

    本函数只 flush，不 commit。
    """
    if not output_text:
        raise ValueError(
            "AI 分块输出不能为空"
        )

    result = await db.execute(
        select(ReportAIChunk)
        .where(
            ReportAIChunk.id == chunk_id
        )
        .with_for_update()
    )

    chunk = result.scalar_one_or_none()

    if chunk is None:
        raise ValueError(
            f"AI 分块不存在：{chunk_id}"
        )

    if chunk.status != AIChunkStatus.processing.value:
        raise ValueError(
            "只有 processing 状态的分块 "
            "才能标记为 success，"
            f"当前状态：{chunk.status}"
        )

    chunk.output_text = output_text
    chunk.status = AIChunkStatus.success.value
    chunk.last_error = None
    chunk.updated_at = utc_now_naive()

    await db.flush()

    return chunk


async def fail_report_ai_chunk(
    db: AsyncSession,
    chunk_id: int,
    error: Exception | str,
) -> ReportAIChunk:
    """
    将一个 processing 分块标记为失败。

    只增加该分块自己的 retry_count，
    不影响同一报告的其他分块。

    本函数只 flush，不 commit。
    """
    result = await db.execute(
        select(ReportAIChunk)
        .where(
            ReportAIChunk.id == chunk_id
        )
        .with_for_update()
    )

    chunk = result.scalar_one_or_none()

    if chunk is None:
        raise ValueError(
            f"AI 分块不存在：{chunk_id}"
        )

    # 已经成功的结果不允许被迟到的失败任务覆盖。
    if chunk.status == AIChunkStatus.success.value:
        return chunk

    if chunk.status != AIChunkStatus.processing.value:
        raise ValueError(
            "只有 processing 状态的分块 "
            "才能标记为 failed，"
            f"当前状态：{chunk.status}"
        )

    chunk.status = AIChunkStatus.failed.value
    chunk.retry_count = (
        chunk.retry_count or 0
    ) + 1

    chunk.last_error = str(error)[:2000]
    chunk.updated_at = utc_now_naive()

    await db.flush()

    return chunk
