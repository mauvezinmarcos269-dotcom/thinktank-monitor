from __future__ import annotations

import asyncio
import json
import logging
import re

from app.core.config import settings
from app.core.llm import SiliconFlowClient

logger = logging.getLogger(__name__)


# ============================================================
# 全局配置
# ============================================================

ANALYSIS_CHUNK_LENGTH = settings.AI_ANALYSIS_CHUNK_LENGTH
TRANSLATION_CHUNK_LENGTH = settings.AI_TRANSLATION_CHUNK_LENGTH
TRANSLATION_MAX_TOKENS = settings.AI_TRANSLATION_MAX_TOKENS
MAX_RETRY = 2
FINAL_OUTPUT_MAX_RETRY = 4

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

def validate_length(
    text: str,
    min_chars: int,
    field: str,
) -> None:
    """
    校验文本长度，不足则抛出异常以触发重试。
    """
    if len(text) < min_chars:
        raise ValueError(
            f"{field} 长度不足: "
            f"期望至少 {min_chars} 字符，"
            f"实际为 {len(text)} 字符"
        )


def validate_length_range(
    text: str,
    min_chars: int,
    max_chars: int,
    field: str,
) -> None:
    validate_length(
        text,
        min_chars,
        field,
    )

    if len(text) > max_chars:
        raise ValueError(
            f"{field} 长度超出: "
            f"期望不超过 {max_chars} 字符，"
            f"实际为 {len(text)} 字符"
        )


def _clean_json_text(text: str) -> str:
    """
    尝试从 LLM 返回内容中提取 JSON。
    """
    if not text:
        raise ValueError("LLM 返回为空")

    text = text.strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = text.strip()

    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]

        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    raise ValueError("LLM 返回的内容不是有效 JSON")


def _extract_json(text: str) -> dict[str, str]:
    """
    将 LLM 返回内容解析成标准 dict。

    即使 LLM 只返回部分字段，缺失字段也会安全地
    返回空字符串。
    """
    cleaned = _clean_json_text(text)

    data = json.loads(cleaned)

    if not isinstance(data, dict):
        raise ValueError("LLM 返回的 JSON 不是对象")

    required_fields = [
        "translation",
        "summary",
        "commentary",
    ]

    result: dict[str, str] = {}

    for field in required_fields:
        value = data.get(field, "")

        if value is None:
            value = ""

        if not isinstance(value, str):
            value = str(value)

        result[field] = value.strip()

    return result


def _extract_translation_result(
    text: str,
    *,
    min_chars: int,
) -> str:
    """
    提取翻译结果。

    优先解析标准 JSON；如果模型返回了纯译文，
    且长度满足要求，则作为 translation 兜底保存。
    """
    try:
        result = _extract_json(text)
    except ValueError:
        candidate = text.strip()

        candidate = re.sub(
            r"^```(?:json|text)?\s*",
            "",
            candidate,
            flags=re.IGNORECASE,
        )

        candidate = re.sub(
            r"\s*```$",
            "",
            candidate,
            flags=re.IGNORECASE,
        ).strip()

        if (
            not candidate
            or candidate.startswith("{")
            or candidate.startswith("[")
        ):
            raise

        validate_length(
            candidate,
            min_chars,
            "translation",
        )

        logger.warning(
            "Translation returned non-JSON content; "
            "accepted as plain translation, length=%s",
            len(candidate),
        )

        return candidate

    translation = result["translation"]

    if not translation:
        raise ValueError(
            "translation 字段为空"
        )

    validate_length(
        translation,
        min_chars,
        "translation",
    )

    return translation


def _extract_analysis_notes(
    text: str,
) -> str:
    """
    从 LLM 返回的 JSON 中提取 analysis_notes。
    """
    cleaned = _clean_json_text(text)

    data = json.loads(cleaned)

    if not isinstance(data, dict):
        raise ValueError(
            "LLM 返回的 JSON 不是对象"
        )

    value = data.get(
        "analysis_notes",
        "",
    )

    if value is None:
        value = ""

    if not isinstance(value, str):
        value = str(value)

    value = value.strip()

    if not value:
        raise ValueError(
            "analysis_notes 字段为空"
        )

    return value

# ============================================================
# Prompt
# ============================================================
def _build_summary_from_notes_prompt(
    title: str,
    analysis_notes: str,
) -> str:
    return f"""
你正在根据一篇国际关系智库报告的全文分块分析笔记，
生成整篇报告的最终中文摘要。

这些分析笔记已经按报告正文顺序覆盖整篇报告。
你必须综合所有部分，而不能只关注前面的内容。

验收标准：
- summary 最终会按中文字符数校验，必须达到 1500-2000 字符。
- 为提高通过率，建议写到 1650-1800 字符，不要贴近上下限。
- 请写 4 个分论点段落，每段约 410-450 个中文字符。
- 不要把“330-360字”理解为英文 word，也不要写成简短提纲。

你必须只输出一个 JSON 对象。

禁止：
- 不要 Markdown
- 不要 ```json
- 不要解释 JSON
- 不要虚构分析笔记中不存在的信息
- 不要简单逐块复述
- 不要重复相同观点
- 不要把不同部分中的重复事实反复列出
- 如果不同笔记存在表述差异，应根据整体上下文谨慎综合，
  不要擅自制造新的事实

JSON 必须严格为：

{{
  "summary": "生成1650-1800字符中文摘要，硬性合格范围为1500-2000字符。必须包含4个主要观点，每个观点单独成段，每段约410-450个中文字符。应覆盖整篇报告的研究背景、核心论点、重要事实或案例、政策建议与主要结论，并按照报告整体逻辑组织，而不是简单拼接分块笔记。"
}}

报告标题：
{title}

全文分析笔记：
{analysis_notes}
""".strip()

def _build_commentary_from_notes_prompt(
    title: str,
    analysis_notes: str,
) -> str:
    return f"""
你正在根据一篇国际关系智库报告的全文分块分析笔记，
生成整篇报告的战略评论。

这些分析笔记已经覆盖整篇报告。
你需要在准确理解报告原意的基础上进行综合判断。

验收标准：
- commentary 最终会按中文字符数校验，必须达到 2000-2500 字符。
- 为提高通过率，建议写到 2200-2350 字符，不要贴近上下限。
- 请写 4 个分论点段落，每段约 550-585 个中文字符。
- 不要写成短评或提纲，必须展开深层机制、政策意图和趋势判断。

你必须只输出一个 JSON 对象。

禁止：
- 不要 Markdown
- 不要 ```json
- 不要解释 JSON
- 不要虚构报告或分析笔记中不存在的事实
- 不要简单重复摘要
- 不要逐块机械复述分析笔记
- 如果原报告并不直接涉及中国，
  不要虚构“中国受到直接影响”的事实；
  可以在明确标明分析性质的前提下讨论其潜在战略启示

JSON 必须严格为：

{{
  "commentary": "生成2200-2350字符中文战略评论，硬性合格范围为2000-2500字符。必须包含4个分论点，每个分论点单独成段，每段约550-585个中文字符。必须分析：1. 报告主要观点及其逻辑；2. 报告所反映的政策或战略意图；3. 对中国及国际格局的现实或潜在影响；4. 未来趋势、深层政策问题或国际竞争问题。评论必须建立在全文分析笔记基础上，并区分报告原文观点与进一步战略研判。"
}}

报告标题：
{title}

全文分析笔记：
{analysis_notes}
""".strip()


def _append_length_retry_feedback(
    prompt: str,
    *,
    field: str,
    min_chars: int,
    max_chars: int,
    last_error: Exception | None,
    previous_draft: str | None = None,
) -> str:
    if last_error is None:
        return prompt

    target_ranges = {
        "summary": "1650-1800",
        "commentary": "2200-2350",
    }
    preferred_range = target_ranges.get(
        field,
        f"{min_chars}-{max_chars}",
    )

    draft_section = ""

    if previous_draft:
        draft_section = f"""

上一版 {field} 草稿如下，请在保留其核心判断的基础上扩写，
不要推翻重写，也不要压缩已有内容：
{previous_draft}
""".rstrip()

    error_text = str(last_error)

    if "长度超出" in error_text:
        adjustment = (
            "请压缩冗余表述，保留4个分论点和核心判断，"
            "把每段控制得更紧凑，使最终结果回到目标区间。"
        )
    else:
        adjustment = (
            "请显著扩写每个分论点，补充因果链条、政策背景、"
            "事实依据和战略含义。"
        )

    return f"""
{prompt}

上一次生成未通过长度校验：
{type(last_error).__name__}: {last_error}
{draft_section}

请重新生成 {field} 字段，必须达到 {min_chars}-{max_chars} 个中文字符。
为避免再次贴近边界，建议控制在 {preferred_range} 个中文字符。
{adjustment}
如果上一版只是略短，请优先补足分析深度；如果上一版超出上限，
请删去重复铺陈和空泛句，保留最关键的事实、逻辑和研判。
仍然只能输出一个 JSON 对象，不能输出解释。
""".strip()

def _build_translation_prompt(
    title: str,
    content: str,
) -> str:
    return f"""
你现在执行的是“全文翻译任务”，不是摘要、概括、分析或评论任务。

请将下面提供的英文智库报告正文完整翻译成中文。

必须严格遵守以下要求：

1. 必须逐段完整翻译输入正文，不得摘要、概括、压缩、删减或跳过任何实质性内容。
2. 必须保留原文的信息量、论证过程、事实、数据、案例、机构名称、人名、地名、时间、数字以及政策表述。
3. 必须尽量保持原文的标题、章节、小标题、段落和列举结构。
4. 不得因为某一段看起来重复、次要或属于背景介绍而省略。
5. 不得自行增加原文中不存在的观点、解释、评论或结论。
6. 专有名词首次出现时，可采用“中文译名（英文原名）”；后续可使用中文译名。
7. 输入内容只是整篇报告的一个分块，也必须完整翻译当前分块，不要尝试总结整篇报告。
8. 如果输入在句子中间开始或结束，只翻译实际提供的内容，不得自行补写缺失上下文。

你必须只输出中文译文正文。

禁止：
- 不要 Markdown
- 不要 ```
- 不要解释任务
- 不要输出摘要
- 不要输出分析
- 不要输出评论
- 不要输出 JSON
- 不要添加“以下是翻译”等说明性文字

报告标题：
{title}

需要完整翻译的正文：
{content}
""".strip()

def _build_analysis_notes_prompt(
    title: str,
    content: str,
    chunk_index: int,
    chunk_count: int,
) -> str:
    """
    为报告的一个正文分块生成结构化分析笔记。
    """
    return f"""
你正在阅读一篇国际关系智库报告的第
{chunk_index}/{chunk_count} 部分。

你的任务不是生成最终摘要或评论，
而是提取这一部分中值得保留的事实、论点和证据，
供后续对整篇报告进行综合分析。

你必须只输出一个 JSON 对象。

禁止：
- 不要 Markdown
- 不要 ```json
- 不要解释 JSON
- 不要虚构报告未提供的信息
- 不要把这一部分误当成整篇报告
- 不要输出 JSON 之外的内容

JSON 必须严格为：

{{
  "analysis_notes": "用中文生成约400-700字的分析笔记。优先保留：1. 本部分的核心论点；2. 重要事实、数据、案例和政策主张；3. 涉及中国、中美关系、国际竞争、科技、产业链、安全或国际秩序的内容；4. 作者的因果判断和政策建议。若本部分不涉及中国，不要强行添加中国内容。"
}}

报告标题：
{title}

当前部分：
第 {chunk_index}/{chunk_count} 部分

当前部分正文：
{content}
""".strip()


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

    translation_min_length = max(
        120,
        int(len(content) * 0.15),
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
                prompt=prompt,
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
            )

            validate_length(
                translation,
                translation_min_length,
                "translation",
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
                    min_chars=1500,
                    max_chars=2000,
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
                1500,
                2000,
                "summary",
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
                    min_chars=2000,
                    max_chars=2500,
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
                2000,
                2500,
                "commentary",
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

