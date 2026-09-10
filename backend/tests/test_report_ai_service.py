import json

import pytest

from app.services.ai.report_ai_service import (
    generate_commentary_from_notes,
    generate_summary_from_notes,
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


@pytest.mark.asyncio
async def test_summary_retry_prompt_includes_length_feedback() -> None:
    short_summary = "短摘要。" * 100
    valid_summary = "足够长的摘要。" * 220
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
    assert "必须达到 1500-2000 个中文字符" in client.prompts[1]
    assert "上一版 summary 草稿如下" in client.prompts[1]
    assert short_summary in client.prompts[1]


@pytest.mark.asyncio
async def test_commentary_retry_prompt_includes_length_feedback() -> None:
    short_commentary = "短评论。" * 150
    valid_commentary = "足够长的评论。" * 300
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
    assert "建议控制在 2200-2350 个中文字符" in client.prompts[1]
    assert "上一版 commentary 草稿如下" in client.prompts[1]
    assert short_commentary in client.prompts[1]


@pytest.mark.asyncio
async def test_commentary_retry_prompt_handles_over_max_draft() -> None:
    short_commentary = "短评论。" * 150
    long_commentary = "过长评论。" * 700
    valid_commentary = "合格评论。" * 430
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
    short_commentary = "短评论。" * 150
    long_commentary = "过长评论。" * 700
    still_long_commentary = "仍然过长。" * 560
    valid_commentary = "合格评论。" * 430
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
    assert "建议控制在 2200-2350 个中文字符" in client.prompts[3]
    assert still_long_commentary in client.prompts[3]
