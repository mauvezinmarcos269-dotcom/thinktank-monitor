from types import SimpleNamespace

from app.schemas.institution import CrawlCandidateListResponse
from app.services.crawl_candidate_service import (
    CANDIDATE_STATUS_SAVED,
    CANDIDATE_STATUS_SKIPPED,
    CrawlCandidateService,
    get_candidate_status_label,
    get_skip_reason_label,
    mark_candidate_saved,
    mark_candidate_skipped,
)


def test_get_skip_reason_label_returns_chinese_label() -> None:
    assert get_skip_reason_label("duplicate_existing") == "已入库重复"


def test_get_candidate_status_label_returns_chinese_label() -> None:
    assert get_candidate_status_label("saved") == "已入库"


def test_mark_candidate_skipped_sets_status_reason_and_error() -> None:
    candidate = SimpleNamespace(
        status="discovered",
        skip_reason_code=None,
        skip_reason_label=None,
        error=None,
    )

    mark_candidate_skipped(
        candidate,
        reason_code="document_failed",
        error="报告页数不足",
    )

    assert candidate.status == CANDIDATE_STATUS_SKIPPED
    assert candidate.skip_reason_code == "document_failed"
    assert candidate.skip_reason_label == "PDF 获取或页数/文本检查失败"
    assert candidate.error == "报告页数不足"


def test_mark_candidate_saved_links_report_and_clears_skip_reason() -> None:
    candidate = SimpleNamespace(
        status="skipped",
        report_id=None,
        skip_reason_code="duplicate_existing",
        skip_reason_label="已入库重复",
        error="old",
    )

    mark_candidate_saved(candidate, report_id=12)

    assert candidate.status == CANDIDATE_STATUS_SAVED
    assert candidate.report_id == 12
    assert candidate.skip_reason_code is None
    assert candidate.skip_reason_label is None
    assert candidate.error is None


def test_candidate_list_response_exposes_pagination_fields() -> None:
    response = CrawlCandidateListResponse(
        items=[],
        total=120,
        skip=50,
        limit=50,
    )

    assert response.total == 120
    assert response.skip == 50
    assert response.limit == 50


def test_format_bool_for_csv() -> None:
    service = CrawlCandidateService()

    assert service._format_bool(True) == "是"
    assert service._format_bool(False) == "否"
    assert service._format_bool(None) == "未判断"
