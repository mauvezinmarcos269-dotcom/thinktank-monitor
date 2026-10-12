from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.services.crawl_quality_service import CrawlQualityStats
from app.services.crawler.candidate_duplicate_service import (
    build_candidate_duplicate_index,
    mark_duplicate_candidate,
)


def _candidate(
    *,
    normalized_url: str,
    pdf_url: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        normalized_url=normalized_url,
        pdf_url=pdf_url,
        status="discovered",
        skip_reason_code=None,
        skip_reason_label=None,
        error=None,
    )


async def test_duplicate_index_matches_reports_and_pending_candidates() -> None:
    report_result = MagicMock()
    report_result.all.return_value = [
        SimpleNamespace(
            normalized_url="https://example.org/report",
            pdf_url="https://example.org/report.pdf",
        )
    ]
    pending_result = MagicMock()
    pending_result.all.return_value = [
        SimpleNamespace(
            normalized_url="https://example.org/pending",
            pdf_url="https://example.org/pending.pdf",
        )
    ]
    db = SimpleNamespace(
        execute=AsyncMock(side_effect=[report_result, pending_result]),
    )
    candidates = [
        _candidate(normalized_url="https://example.org/report"),
        _candidate(
            normalized_url="https://example.org/other",
            pdf_url="https://example.org/pending.pdf",
        ),
        _candidate(normalized_url="https://example.org/new"),
    ]

    index = await build_candidate_duplicate_index(
        db,
        candidates=candidates,
        exclude_crawl_run_id=88,
    )

    assert index.classify(candidates[0]) == "report"
    assert index.classify(candidates[1]) == "pending_candidate"
    assert index.classify(candidates[2]) is None
    pending_query = db.execute.await_args_list[1].args[0].compile()
    assert "pending_relevance" in pending_query.params.values()
    assert 88 in pending_query.params.values()


async def test_duplicate_index_ignores_candidates_without_identity() -> None:
    db = SimpleNamespace(execute=AsyncMock())

    index = await build_candidate_duplicate_index(
        db,
        candidates=[_candidate(normalized_url="", pdf_url=None)],
        exclude_crawl_run_id=1,
    )

    assert index.classify(_candidate(normalized_url="")) is None
    db.execute.assert_not_awaited()


def test_mark_pending_duplicate_uses_distinct_reason_and_summary() -> None:
    candidate = _candidate(normalized_url="https://example.org/pending")
    stats = CrawlQualityStats(raw_candidates=1, unique_candidates=1)

    handled = mark_duplicate_candidate(
        candidate,
        duplicate_kind="pending_candidate",
        quality_stats=stats,
        url=candidate.normalized_url,
    )

    assert handled
    assert candidate.status == "skipped"
    assert candidate.skip_reason_code == "duplicate_pending"
    assert candidate.skip_reason_label == "已有待授权候选"
    assert stats.duplicate_pending == 1
    assert "已有待授权候选 1 条" in (stats.to_summary() or "")


def test_mark_report_duplicate_preserves_existing_reason() -> None:
    candidate = _candidate(normalized_url="https://example.org/report")
    stats = CrawlQualityStats(raw_candidates=1, unique_candidates=1)

    handled = mark_duplicate_candidate(
        candidate,
        duplicate_kind="report",
        quality_stats=stats,
        url=candidate.normalized_url,
    )

    assert handled
    assert candidate.status == "skipped"
    assert candidate.skip_reason_code == "duplicate_existing"
    assert candidate.skip_reason_label == "已入库重复"
    assert stats.duplicate_existing == 1
