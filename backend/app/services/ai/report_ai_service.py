from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.core.llm import SiliconFlowClient
from app.services.ai.report_ai_output import (
    extract_analysis_notes as _extract_analysis_notes,
)
from app.services.ai.report_ai_output import (
    extract_json as _extract_json,
)
from app.services.ai.report_ai_output import (
    extract_translation_result as _extract_translation_result,
)
from app.services.ai.report_ai_output import (
    maximum_translation_length,
    minimum_translation_length,
    validate_length,
    validate_length_range,
    validate_numbered_points,
    validate_translation_completeness,
)
from app.services.ai.report_ai_prompts import (
    append_length_retry_feedback as _append_length_retry_feedback,
)
from app.services.ai.report_ai_prompts import (
    append_translation_retry_feedback as _append_translation_retry_feedback,
)
from app.services.ai.report_ai_prompts import (
    build_analysis_notes_prompt as _build_analysis_notes_prompt,
)
from app.services.ai.report_ai_prompts import (
    build_commentary_from_notes_prompt as _build_commentary_from_notes_prompt,
)
from app.services.ai.report_ai_prompts import (
    build_summary_from_notes_prompt as _build_summary_from_notes_prompt,
)
from app.services.ai.report_ai_prompts import (
    build_translation_prompt as _build_translation_prompt,
)

logger = logging.getLogger(__name__)


# ============================================================
# 全局配置
# ============================================================

ANALYSIS_CHUNK_LENGTH = settings.AI_ANALYSIS_CHUNK_LENGTH
TRANSLATION_CHUNK_LENGTH = settings.AI_TRANSLATION_CHUNK_LENGTH
TRANSLATION_MAX_TOKENS = settings.AI_TRANSLATION_MAX_TOKENS
MAX_RETRY = 2
FINAL_OUTPUT_MAX_RETRY = 4
SUMMARY_MIN_CHARS = 1500
SUMMARY_MAX_CHARS = 2200
COMMENTARY_MIN_CHARS = 2000
COMMENTARY_MAX_CHARS = 2500

AI_SEMAPHORE = asyncio.Semaphore(3)


def _split_text_into_chunks(
    content: str,
    chunk_length: int = TRANSLATION_CHUNK_LENGTH,
) -> list[str]:
    """
    将长报告切分为多个翻译块。

    优先在换行处切分，并保证所有分块重新拼接后
    与原始正文完全一致，不丢字符、不重复字符。
    """
    if not content:
        return []

    if not content.strip():
        return []

    if len(content) <= chunk_length:
        return [content]

    chunks: list[str] = []
    start = 0
    content_length = len(content)

    while start < content_length:
        end = min(
            start + chunk_length,
            content_length,
        )

        if end < content_length:
            search_start = max(
                start,
                end - 2000,
            )

            newline_position = content.rfind(
                "\n",
                search_start,
                end,
            )

            if newline_position > start:
                end = newline_position + 1

        chunk = content[start:end]

        if chunk:
            chunks.append(chunk)

        start = end

    return chunks

def _split_analysis_chunks(
    content: str,
) -> list[str]:
    """
    将完整报告切分为分析块。

    分析块允许比翻译块更大，
    后续用于提取每一部分的结构化分析笔记。
    """
    return _split_text_into_chunks(
        content,
        chunk_length=ANALYSIS_CHUNK_LENGTH,
    )

# ============================================================
# LLM 请求封装
# ============================================================

async def _safe_chat(
    client: SiliconFlowClient,
    *,
    prompt: str,
    temperature: float,
    max_tokens: int,
    response_format_json: bool = True,
) -> str:
    """
    带并发限制的 LLM 请求。

    Semaphore 只限制“当前正在执行的 API 请求”，
    不会把 translation / summary / commentary 重新变成串行任务。

    例如 AI_SEMAPHORE=3：

        translation ─┐
        summary ──────┼── 最多同时3个请求
        commentary ───┘

    当未来 worker 同时处理多个 report 时，
    也能控制整个 worker 进程的 LLM 并发量。
    """
    async with AI_SEMAPHORE:
        return await client.chat(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format_json=response_format_json,
        )

async def generate_analysis_notes(
    client: SiliconFlowClient,
    title: str,
    content: str,
    chunk_index: int,
    chunk_count: int,
) -> str:
    """
    为单个报告分块生成分析笔记。
    """
    prompt = _build_analysis_notes_prompt(
        title,
        content,
        chunk_index,
        chunk_count,
    )

    last_error: Exception | None = None

    for attempt in range(
        1,
        MAX_RETRY + 1,
    ):
        try:
            logger.info(
                "Starting analysis notes "
                "attempt %s/%s for chunk %s/%s, "
                "content_len=%s",
                attempt,
                MAX_RETRY,
                chunk_index,
                chunk_count,
                len(content),
            )

            raw_result = await _safe_chat(
                client,
                prompt=prompt,
                temperature=0.1,
                max_tokens=1800,
            )

            notes = _extract_analysis_notes(
                raw_result
            )

            validate_length(
                notes,
                200,
                "analysis_notes",
            )

            logger.info(
                "Analysis notes succeeded "
                "for chunk %s/%s, notes_len=%s",
                chunk_index,
                chunk_count,
                len(notes),
            )

            return notes

        except Exception as exc:
            last_error = exc

            logger.exception(
                "Analysis notes attempt "
                "%s/%s failed for chunk %s/%s: "
                "%r [%s]",
                attempt,
                MAX_RETRY,
                chunk_index,
                chunk_count,
                exc,
                type(exc).__name__,
            )

    raise ValueError(
        "分析笔记生成失败: "
        f"{type(last_error).__name__}: "
        f"{last_error}"
    )

# ============================================================
# Translation
# ============================================================

async def generate_translation(
    client: SiliconFlowClient,
    title: str,
    content: str,
) -> str:
    prompt = _build_translation_prompt(
        title,
        content,
    )

    last_error: Exception | None = None

    translation_min_length = (
        minimum_translation_length(
            content
        )
    )
    translation_max_length = (
        maximum_translation_length(
            content
        )
    )

    for attempt in range(1, MAX_RETRY + 1):
        try:
            logger.info(
                "Starting translation attempt %s/%s, content_len=%s",
                attempt,
                MAX_RETRY,
                len(content),
            )

            raw_result = await _safe_chat(
                client,
                prompt=_append_translation_retry_feedback(
                    prompt,
                    min_chars=translation_min_length,
                    max_chars=translation_max_length,
                    last_error=last_error,
                ),
                temperature=0.1,
                max_tokens=TRANSLATION_MAX_TOKENS,
                response_format_json=False,
            )

            logger.info(
                "Translation attempt %s returned %s chars",
                attempt,
                len(raw_result) if raw_result else 0,
            )

            translation = _extract_translation_result(
                raw_result,
                min_chars=translation_min_length,
                max_chars=translation_max_length,
            )

            validate_translation_completeness(
                translation,
                content,
            )

            logger.info(
                "Translation succeeded on attempt %s",
                attempt,
            )

            return translation

        except Exception as exc:
            last_error = exc

            logger.exception(
                "Translation attempt %s/%s failed: %r [%s]",
                attempt,
                MAX_RETRY,
                exc,
                type(exc).__name__,
            )

    logger.error(
        "Translation failed after %s attempts; "
        "last_error=%r [%s]",
        MAX_RETRY,
        last_error,
        type(last_error).__name__
        if last_error
        else "Unknown",
    )

    raise ValueError(
        f"翻译生成失败: "
        f"{type(last_error).__name__}: {last_error}"
    )


# ============================================================
# Summary
# ============================================================



async def generate_summary_from_notes(
    client: SiliconFlowClient,
    title: str,
    analysis_notes: str,
) -> str:
    """
    根据覆盖全文的分析笔记生成最终中文摘要。
    """
    prompt = _build_summary_from_notes_prompt(
        title,
        analysis_notes,
    )

    last_error: Exception | None = None
    previous_draft: str | None = None

    for attempt in range(
        1,
        FINAL_OUTPUT_MAX_RETRY + 1,
    ):
        try:
            logger.info(
                "Starting full-report summary "
                "attempt %s/%s, notes_len=%s",
                attempt,
                FINAL_OUTPUT_MAX_RETRY,
                len(analysis_notes),
            )

            raw_result = await _safe_chat(
                client,
                prompt=_append_length_retry_feedback(
                    prompt,
                    field="summary",
                    min_chars=SUMMARY_MIN_CHARS,
                    max_chars=SUMMARY_MAX_CHARS,
                    last_error=last_error,
                    previous_draft=previous_draft,
                ),
                temperature=0.1,
                max_tokens=2800,
            )

            result = _extract_json(
                raw_result
            )

            if not result["summary"]:
                raise ValueError(
                    "summary 字段为空"
                )

            previous_draft = result["summary"]

            validate_length_range(
                result["summary"],
                SUMMARY_MIN_CHARS,
                SUMMARY_MAX_CHARS,
                "summary",
            )
            validate_numbered_points(
                result["summary"],
                min_points=4,
                field="summary",
            )

            logger.info(
                "Full-report summary succeeded "
                "on attempt %s, summary_len=%s",
                attempt,
                len(result["summary"]),
            )

            return result["summary"]

        except Exception as exc:
            last_error = exc

            logger.exception(
                "Full-report summary attempt "
                "%s/%s failed: %r [%s]",
                attempt,
                FINAL_OUTPUT_MAX_RETRY,
                exc,
                type(exc).__name__,
            )

    raise ValueError(
        "全文摘要生成失败: "
        f"{type(last_error).__name__}: "
        f"{last_error}"
    )

# ============================================================
# Commentary
# ============================================================


async def generate_commentary_from_notes(
    client: SiliconFlowClient,
    title: str,
    analysis_notes: str,
) -> str:
    """
    根据覆盖全文的分析笔记生成最终战略评论。
    """
    prompt = _build_commentary_from_notes_prompt(
        title,
        analysis_notes,
    )

    last_error: Exception | None = None
    previous_draft: str | None = None

    for attempt in range(
        1,
        FINAL_OUTPUT_MAX_RETRY + 1,
    ):
        try:
            logger.info(
                "Starting full-report commentary "
                "attempt %s/%s, notes_len=%s",
                attempt,
                FINAL_OUTPUT_MAX_RETRY,
                len(analysis_notes),
            )

            raw_result = await _safe_chat(
                client,
                prompt=_append_length_retry_feedback(
                    prompt,
                    field="commentary",
                    min_chars=COMMENTARY_MIN_CHARS,
                    max_chars=COMMENTARY_MAX_CHARS,
                    last_error=last_error,
                    previous_draft=previous_draft,
                ),
                temperature=0.1,
                max_tokens=3600,
            )

            result = _extract_json(
                raw_result
            )

            if not result["commentary"]:
                raise ValueError(
                    "commentary 字段为空"
                )

            previous_draft = result["commentary"]

            validate_length_range(
                result["commentary"],
                COMMENTARY_MIN_CHARS,
                COMMENTARY_MAX_CHARS,
                "commentary",
            )
            validate_numbered_points(
                result["commentary"],
                min_points=4,
                field="commentary",
            )

            logger.info(
                "Full-report commentary succeeded "
                "on attempt %s, commentary_len=%s",
                attempt,
                len(result["commentary"]),
            )

            return result["commentary"]

        except Exception as exc:
            last_error = exc

            logger.exception(
                "Full-report commentary attempt "
                "%s/%s failed: %r [%s]",
                attempt,
                FINAL_OUTPUT_MAX_RETRY,
                exc,
                type(exc).__name__,
            )

    raise ValueError(
        "全文评论生成失败: "
        f"{type(last_error).__name__}: "
        f"{last_error}"
    )

