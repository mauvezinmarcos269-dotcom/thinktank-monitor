import pytest

from app.services.ai import report_ai_finalizer_runner as runner


@pytest.mark.asyncio
async def test_generate_final_outputs_reuses_existing_commentary(
    monkeypatch,
) -> None:
    calls: list[str] = []

    async def fake_summary(client, title, analysis_notes):
        calls.append("summary")
        return "合格摘要"

    async def fake_commentary(client, title, analysis_notes):
        calls.append("commentary")
        return "不应重新生成"

    monkeypatch.setattr(
        runner,
        "generate_summary_from_notes",
        fake_summary,
    )
    monkeypatch.setattr(
        runner,
        "generate_commentary_from_notes",
        fake_commentary,
    )

    result = await runner._generate_final_report_outputs(
        object(),
        title="Sample title",
        analysis_notes="分析笔记",
        existing_commentary="已保存评论",
    )

    assert result.summary == "合格摘要"
    assert result.commentary == "已保存评论"
    assert result.errors == ()
    assert calls == ["summary"]


@pytest.mark.asyncio
async def test_generate_final_outputs_keeps_successful_partial_result(
    monkeypatch,
) -> None:
    async def fake_summary(client, title, analysis_notes):
        raise ValueError("summary 长度不足")

    async def fake_commentary(client, title, analysis_notes):
        return "合格评论"

    monkeypatch.setattr(
        runner,
        "generate_summary_from_notes",
        fake_summary,
    )
    monkeypatch.setattr(
        runner,
        "generate_commentary_from_notes",
        fake_commentary,
    )

    result = await runner._generate_final_report_outputs(
        object(),
        title="Sample title",
        analysis_notes="分析笔记",
    )

    assert result.summary is None
    assert result.commentary == "合格评论"
    assert len(result.errors) == 1
    assert "summary 长度不足" in str(result.errors[0])
