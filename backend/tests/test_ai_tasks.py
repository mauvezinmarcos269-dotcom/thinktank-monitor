import pytest

from app.workers import ai_tasks, report_tasks


@pytest.mark.asyncio
async def test_legacy_run_ai_analysis_redirects_to_chunk_scheduler(monkeypatch):
    calls = []

    async def fake_enqueue_ai_chunk_tasks(
        report_limit,
        chunk_limit,
        only_report_id=None,
    ):
        calls.append(
            {
                "report_limit": report_limit,
                "chunk_limit": chunk_limit,
                "only_report_id": only_report_id,
            }
        )
        return [101, 102]

    monkeypatch.setattr(
        report_tasks,
        "_enqueue_ai_chunk_tasks",
        fake_enqueue_ai_chunk_tasks,
    )

    result = await ai_tasks._run_ai_analysis(
        1,
        "legacy-lock-token",
    )

    assert result == {
        "status": "queued",
        "report_id": 1,
        "chunk_ids": [101, 102],
    }
    assert calls == [
        {
            "report_limit": 1,
            "chunk_limit": 50,
            "only_report_id": 1,
        }
    ]


@pytest.mark.asyncio
async def test_legacy_run_ai_analysis_reports_skipped_when_no_chunks(monkeypatch):
    async def fake_enqueue_ai_chunk_tasks(
        report_limit,
        chunk_limit,
        only_report_id=None,
    ):
        return []

    monkeypatch.setattr(
        report_tasks,
        "_enqueue_ai_chunk_tasks",
        fake_enqueue_ai_chunk_tasks,
    )

    result = await ai_tasks._run_ai_analysis(1)

    assert result == {
        "status": "skipped",
        "report_id": 1,
        "chunk_ids": [],
    }


@pytest.mark.asyncio
async def test_legacy_enqueue_pending_ai_tasks_redirects_to_chunk_scheduler(
    monkeypatch,
):
    calls = []

    async def fake_enqueue_ai_chunk_tasks(
        report_limit,
        chunk_limit,
        only_report_id=None,
    ):
        calls.append(
            {
                "report_limit": report_limit,
                "chunk_limit": chunk_limit,
                "only_report_id": only_report_id,
            }
        )
        return [201]

    monkeypatch.setattr(
        report_tasks,
        "_enqueue_ai_chunk_tasks",
        fake_enqueue_ai_chunk_tasks,
    )

    result = await report_tasks._enqueue_pending_ai_tasks(7)

    assert result == [201]
    assert calls == [
        {
            "report_limit": 7,
            "chunk_limit": 50,
            "only_report_id": None,
        }
    ]
