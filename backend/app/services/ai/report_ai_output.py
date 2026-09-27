from __future__ import annotations

import json
import logging
import re

MIN_TRANSLATION_SOURCE_LENGTH_RATIO = 0.35
MIN_TRANSLATION_ACCEPTANCE_RATIO = 0.60
MIN_TRANSLATION_LENGTH_FLOOR = 40
MAX_TRANSLATION_SOURCE_LENGTH_RATIO = 2.0
MAX_TRANSLATION_LENGTH_FLOOR = 5000

logger = logging.getLogger(__name__)


def validate_length(
    text: str,
    min_chars: int,
    field: str,
) -> None:
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


def _effective_source_length(text: str) -> int:
    normalized = re.sub(
        r"(?:\.\s*){4,}",
        "",
        text,
    )
    return len(
        re.sub(
            r"\s+",
            "",
            normalized,
        )
    )


def minimum_translation_length(
    source_content: str,
) -> int:
    return max(
        MIN_TRANSLATION_LENGTH_FLOOR,
        int(
            _effective_source_length(source_content)
            * MIN_TRANSLATION_SOURCE_LENGTH_RATIO
        ),
    )


def maximum_translation_length(
    source_content: str,
) -> int:
    return max(
        MAX_TRANSLATION_LENGTH_FLOOR,
        int(
            _effective_source_length(source_content)
            * MAX_TRANSLATION_SOURCE_LENGTH_RATIO
        ),
    )


def _minimum_translation_acceptance_length(
    target_min_chars: int,
) -> int:
    return max(
        MIN_TRANSLATION_LENGTH_FLOOR,
        int(
            target_min_chars
            * MIN_TRANSLATION_ACCEPTANCE_RATIO
        ),
    )


def _validate_translation_length_bounds(
    translation: str,
    *,
    min_chars: int,
    max_chars: int,
) -> None:
    hard_min_chars = (
        _minimum_translation_acceptance_length(
            min_chars
        )
    )

    validate_length_range(
        translation,
        hard_min_chars,
        max_chars,
        "translation",
    )


def validate_translation_completeness(
    translation: str,
    source_content: str,
) -> None:
    min_chars = minimum_translation_length(
        source_content
    )
    max_chars = maximum_translation_length(
        source_content
    )
    hard_min_chars = (
        _minimum_translation_acceptance_length(
            min_chars
        )
    )

    _validate_translation_length_bounds(
        translation,
        min_chars=min_chars,
        max_chars=max_chars,
    )

    if len(translation) < min_chars:
        logger.warning(
            "Translation slightly below target length; "
            "accepted for manual review: target=%s, "
            "hard_min=%s, actual=%s",
            min_chars,
            hard_min_chars,
            len(translation),
        )

    normalized_prefix = translation.strip()[:80]
    summary_like_patterns = (
        "以下是摘要",
        "以下为摘要",
        "摘要如下",
        "简要概括",
        "简要总结",
        "summary:",
        "brief summary",
    )

    if any(
        pattern in normalized_prefix.lower()
        for pattern in summary_like_patterns
    ):
        raise ValueError(
            "translation 疑似摘要式输出，"
            "未按全文翻译要求返回译文"
        )


def clean_json_text(text: str) -> str:
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


def extract_json(text: str) -> dict[str, str]:
    cleaned = clean_json_text(text)

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


def extract_translation_result(
    text: str,
    *,
    min_chars: int,
    max_chars: int | None = None,
) -> str:
    try:
        result = extract_json(text)
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

        _validate_translation_length_bounds(
            candidate,
            min_chars=min_chars,
            max_chars=max_chars
            if max_chars is not None
            else MAX_TRANSLATION_LENGTH_FLOOR,
        )

        if len(candidate) < min_chars:
            hard_min_chars = (
                _minimum_translation_acceptance_length(
                    min_chars
                )
            )
            logger.warning(
                "Plain translation below target length; "
                "accepted for manual review: target=%s, "
                "hard_min=%s, actual=%s",
                min_chars,
                hard_min_chars,
                len(candidate),
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

    _validate_translation_length_bounds(
        translation,
        min_chars=min_chars,
        max_chars=max_chars
        if max_chars is not None
        else MAX_TRANSLATION_LENGTH_FLOOR,
    )

    if len(translation) < min_chars:
        hard_min_chars = (
            _minimum_translation_acceptance_length(
                min_chars
            )
        )
        logger.warning(
            "JSON translation below target length; "
            "accepted for manual review: target=%s, "
            "hard_min=%s, actual=%s",
            min_chars,
            hard_min_chars,
            len(translation),
        )

    return translation


def extract_analysis_notes(
    text: str,
) -> str:
    cleaned = clean_json_text(text)

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
