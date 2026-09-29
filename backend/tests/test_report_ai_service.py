import json

import pytest

from app.services.ai.report_ai_prompts import (
    build_commentary_from_notes_prompt,
    build_summary_from_notes_prompt,
)
from app.services.ai.report_ai_service import (
    generate_commentary_from_notes,
    generate_summary_from_notes,
    generate_translation,
    maximum_translation_length,
    minimum_translation_length,
    validate_translation_completeness,
)


def build_numbered_text(
    *,
    prefix: str,
    repeats: int,
    points: int = 4,
) -> str:
    numerals = [
        "一",
        "二",
        "三",
        "四",
        "五",
    ]

    return "\n\n".join(
        f"{numerals[index]}、{prefix}{index + 1}。"
        + ("这是用于测试的充分展开内容。" * repeats)
        for index in range(points)
    )


class FakeClient:
    def __init__(self, responses: list[str]):
        self.responses = responses
        self.prompts: list[str] = []

    async def chat(
        self,
        *,
        prompt: str,
        temperature: float,
        max_tokens: int,
        response_format_json: bool = True,
    ) -> str:
        self.prompts.append(prompt)
        return self.responses.pop(0)


def test_summary_prompt_requires_numbered_points() -> None:
    prompt = build_summary_from_notes_prompt(
        "Sample title",
        "分析笔记。",
    )

    assert "必须包含4个及以上主要观点" in prompt
    assert "必须依次使用“一、”“二、”“三、”“四、”" in prompt
    assert "不要使用无编号的连续段落" in prompt


def test_commentary_prompt_requires_numbered_points() -> None:
    prompt = build_commentary_from_notes_prompt(
        "Sample title",
        "分析笔记。",
    )

    assert "必须包含4个及以上分论点" in prompt
    assert "建议写到5个" in prompt
    assert "必须依次使用“一、”“二、”“三、”“四、”" in prompt
    assert "不要使用无编号的连续段落" in prompt


@pytest.mark.asyncio
async def test_summary_retry_prompt_includes_length_feedback() -> None:
    short_summary = build_numbered_text(prefix="短观点", repeats=8)
    valid_summary = build_numbered_text(prefix="合格观点", repeats=34)
    client = FakeClient(
        [
            json.dumps({"summary": short_summary}, ensure_ascii=False),
            json.dumps({"summary": valid_summary}, ensure_ascii=False),
        ]
    )

    summary = await generate_summary_from_notes(
        client,
        "Sample title",
        "分析笔记。" * 200,
    )

    assert summary == valid_summary
    assert len(client.prompts) == 2
    assert "上一次生成未通过长度校验" in client.prompts[1]
    assert "summary 长度不足" in client.prompts[1]
    assert "必须达到 1500-2200 个中文字符" in client.prompts[1]
    assert "上一版 summary 草稿如下" in client.prompts[1]
    assert short_summary in client.prompts[1]


@pytest.mark.asyncio
async def test_summary_retry_prompt_includes_numbered_point_feedback() -> None:
    unnumbered_summary = "没有编号的主要观点。" * 170
    valid_summary = build_numbered_text(prefix="合格观点", repeats=34)
    client = FakeClient(
        [
            json.dumps({"summary": unnumbered_summary}, ensure_ascii=False),
            json.dumps({"summary": valid_summary}, ensure_ascii=False),
        ]
    )

    summary = await generate_summary_from_notes(
        client,
        "Sample title",
        "分析笔记。" * 200,
    )

    assert summary == valid_summary
    assert "summary 分论点不足" in client.prompts[1]
    assert "必须显式使用“一、”“二、”“三、”“四、”" in client.prompts[1]


@pytest.mark.asyncio
async def test_summary_accepts_slightly_over_legacy_upper_bound() -> None:
    legacy_over_limit_summary = build_numbered_text(
        prefix="较长主要观点",
        repeats=36,
    )
    client = FakeClient(
        [
            json.dumps(
                {"summary": legacy_over_limit_summary},
                ensure_ascii=False,
            ),
        ]
    )

    summary = await generate_summary_from_notes(
        client,
        "Sample title",
        "分析笔记。" * 200,
    )

    assert summary == legacy_over_limit_summary
    assert 2000 < len(summary) <= 2200


@pytest.mark.asyncio
async def test_summary_still_rejects_clearly_over_new_upper_bound() -> None:
    too_long_summary = build_numbered_text(
        prefix="过长主要观点",
        repeats=90,
    )
    client = FakeClient(
        [
            json.dumps(
                {"summary": too_long_summary},
                ensure_ascii=False,
            ),
            json.dumps(
                {"summary": too_long_summary},
                ensure_ascii=False,
            ),
            json.dumps(
                {"summary": too_long_summary},
                ensure_ascii=False,
            ),
            json.dumps(
                {"summary": too_long_summary},
                ensure_ascii=False,
            ),
        ]
    )

    with pytest.raises(ValueError, match="全文摘要生成失败"):
        await generate_summary_from_notes(
            client,
            "Sample title",
            "分析笔记。" * 200,
        )


@pytest.mark.asyncio
async def test_commentary_retry_prompt_includes_length_feedback() -> None:
    short_commentary = build_numbered_text(prefix="短研判", repeats=12)
    valid_commentary = build_numbered_text(prefix="合格研判", repeats=42)
    client = FakeClient(
        [
            json.dumps({"commentary": short_commentary}, ensure_ascii=False),
            json.dumps({"commentary": valid_commentary}, ensure_ascii=False),
        ]
    )

    commentary = await generate_commentary_from_notes(
        client,
        "Sample title",
        "分析笔记。" * 200,
    )

    assert commentary == valid_commentary
    assert len(client.prompts) == 2
    assert "上一次生成未通过长度校验" in client.prompts[1]
    assert "commentary 长度不足" in client.prompts[1]
    assert "必须达到 2000-2500 个中文字符" in client.prompts[1]
    assert "建议控制在 2300-2400 个中文字符" in client.prompts[1]
    assert "上一版 commentary 草稿如下" in client.prompts[1]
    assert short_commentary in client.prompts[1]


@pytest.mark.asyncio
async def test_commentary_retry_prompt_includes_numbered_point_feedback() -> None:
    unnumbered_commentary = "没有编号的深层研判。" * 210
    valid_commentary = build_numbered_text(prefix="合格研判", repeats=42)
    client = FakeClient(
        [
            json.dumps({"commentary": unnumbered_commentary}, ensure_ascii=False),
            json.dumps({"commentary": valid_commentary}, ensure_ascii=False),
        ]
    )

    commentary = await generate_commentary_from_notes(
        client,
        "Sample title",
        "分析笔记。" * 200,
    )

    assert commentary == valid_commentary
    assert "commentary 分论点不足" in client.prompts[1]
    assert "至少必须写满四个编号分论点" in client.prompts[1]


@pytest.mark.asyncio
async def test_commentary_retry_prompt_handles_over_max_draft() -> None:
    short_commentary = build_numbered_text(prefix="短研判", repeats=12)
    long_commentary = build_numbered_text(prefix="过长研判", repeats=140)
    valid_commentary = build_numbered_text(prefix="合格研判", repeats=42)
    client = FakeClient(
        [
            json.dumps({"commentary": short_commentary}, ensure_ascii=False),
            json.dumps({"commentary": long_commentary}, ensure_ascii=False),
            json.dumps({"commentary": valid_commentary}, ensure_ascii=False),
        ]
    )

    commentary = await generate_commentary_from_notes(
        client,
        "Sample title",
        "分析笔记。" * 200,
    )

    assert commentary == valid_commentary
    assert len(client.prompts) == 3
    assert "commentary 长度超出" in client.prompts[2]
    assert "请压缩冗余表述" in client.prompts[2]
    assert long_commentary in client.prompts[2]


@pytest.mark.asyncio
async def test_commentary_allows_four_final_output_attempts() -> None:
    short_commentary = build_numbered_text(prefix="短研判", repeats=12)
    long_commentary = build_numbered_text(prefix="过长研判", repeats=140)
    still_long_commentary = build_numbered_text(
        prefix="仍然过长",
        repeats=115,
    )
    valid_commentary = build_numbered_text(prefix="合格研判", repeats=42)
    client = FakeClient(
        [
            json.dumps({"commentary": short_commentary}, ensure_ascii=False),
            json.dumps({"commentary": long_commentary}, ensure_ascii=False),
            json.dumps(
                {"commentary": still_long_commentary},
                ensure_ascii=False,
            ),
            json.dumps({"commentary": valid_commentary}, ensure_ascii=False),
        ]
    )

    commentary = await generate_commentary_from_notes(
        client,
        "Sample title",
        "分析笔记。" * 200,
    )

    assert commentary == valid_commentary
    assert len(client.prompts) == 4
    assert "commentary 长度超出" in client.prompts[3]
    assert "建议控制在 2200-2300 个中文字符" in client.prompts[3]
    assert still_long_commentary in client.prompts[3]


def test_minimum_translation_length_uses_effective_source_length() -> None:
    source_content = "word " * 1000

    assert minimum_translation_length(source_content) == 1400


def test_minimum_translation_length_ignores_toc_dot_leaders() -> None:
    source_content = (
        "Contents\n"
        "Foreword. . . . . . . . . . . . . . . . . . . . . . . . . . 1\n"
        "Executive Summary. . . . . . . . . . . . . . . . . . . . . 5\n"
        "Introduction: The New Cold War.. . . . . . . . . . . . . 16\n"
    )

    assert minimum_translation_length(source_content) < 80


def test_validate_translation_completeness_rejects_summary_like_output() -> None:
    source_content = "word " * 200
    translation = "以下是摘要：" + ("这是简短说明。" * 60)

    with pytest.raises(ValueError, match="疑似摘要式输出"):
        validate_translation_completeness(
            translation,
            source_content,
        )


def test_validate_translation_completeness_accepts_slightly_short_output() -> None:
    source_content = "word " * 1000
    min_length = minimum_translation_length(source_content)
    translation = "译" * (min_length - 20)

    validate_translation_completeness(
        translation,
        source_content,
    )


def test_validate_translation_completeness_accepts_short_tail_chunk() -> None:
    source_content = (
        "necessarily represent the views of members of the advisory committee, "
        "whose involvement should in no way be interpreted as an endorsement "
        "of the report by either themselves or the organizations with which "
        "they are affiliated."
    )
    translation = (
        "并不必然代表顾问委员会成员的观点，其参与不应被解释为他们本人或其所属组织"
        "对本报告的正式认可或背书。"
    )

    assert minimum_translation_length(source_content) < 120

    validate_translation_completeness(
        translation,
        source_content,
    )


def test_validate_translation_completeness_rejects_tiny_short_tail_output() -> None:
    source_content = (
        "necessarily represent the views of members of the advisory committee, "
        "whose involvement should in no way be interpreted as an endorsement "
        "of the report by either themselves or the organizations with which "
        "they are affiliated."
    )

    with pytest.raises(ValueError, match="translation 长度不足"):
        validate_translation_completeness(
            "略。",
            source_content,
        )


def test_validate_translation_completeness_accepts_moderately_short_output() -> None:
    source_content = "word " * 1000
    min_length = minimum_translation_length(source_content)
    translation = "译" * int(min_length * 0.65)

    validate_translation_completeness(
        translation,
        source_content,
    )


def test_validate_translation_completeness_rejects_clearly_short_output() -> None:
    source_content = "word " * 1000
    min_length = minimum_translation_length(source_content)
    translation = "译" * int(min_length * 0.55)

    with pytest.raises(ValueError, match="translation 长度不足"):
        validate_translation_completeness(
            translation,
            source_content,
        )


def test_validate_translation_completeness_rejects_expanded_output() -> None:
    source_content = "word " * 1000
    max_length = maximum_translation_length(source_content)
    translation = "译" * (max_length + 1)

    with pytest.raises(ValueError, match="translation 长度超出"):
        validate_translation_completeness(
            translation,
            source_content,
        )


@pytest.mark.asyncio
async def test_translation_retry_prompt_includes_completeness_feedback() -> None:
    source_content = "word " * 200
    short_translation = "短译文。" * 10
    valid_translation = "完整译文。" * 80
    client = FakeClient(
        [
            short_translation,
            valid_translation,
        ]
    )

    translation = await generate_translation(
        client,
        "Sample title",
        source_content,
    )

    assert translation == valid_translation
    assert len(client.prompts) == 2
    assert "上一次翻译未通过完整性验收" in client.prompts[1]
    assert "不得改写为摘要、要点、提纲或评论" in client.prompts[1]
    assert "本次译文应控制在" in client.prompts[1]


@pytest.mark.asyncio
async def test_translation_retry_prompt_handles_expanded_output() -> None:
    source_content = "word " * 1000
    expanded_translation = "扩写译文。" * 2000
    valid_translation = "完整译文。" * 300
    client = FakeClient(
        [
            expanded_translation,
            valid_translation,
        ]
    )

    translation = await generate_translation(
        client,
        "Sample title",
        source_content,
    )

    assert translation == valid_translation
    assert len(client.prompts) == 2
    assert "translation 长度超出" in client.prompts[1]
    assert "请只翻译当前输入中实际存在的文字" in client.prompts[1]
