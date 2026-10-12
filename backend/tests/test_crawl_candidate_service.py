import csv
from datetime import datetime
from io import StringIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.llm_authorization import LLMNotAuthorized, document_hash
from app.schemas.institution import CrawlCandidateListResponse
from app.services.crawl_candidate_service import (
    CANDIDATE_STATUS_SAVED,
    CANDIDATE_STATUS_SKIPPED,
    CrawlCandidateService,
    get_candidate_status_label,
    get_content_kind_label,
    get_skip_reason_label,
    mark_candidate_pending_relevance,
    mark_candidate_saved,
    mark_candidate_skipped,
    set_candidate_document_metadata,
)
from app.services.crawler.report_document_service import (
    ReportDocumentResult,
    ReportDocumentValidationError,
)


def test_get_skip_reason_label_returns_chinese_label() -> None:
    assert get_skip_reason_label("duplicate_existing") == "已入库重复"
    assert get_skip_reason_label("duplicate_pending") == "已有待授权候选"
    assert (
        get_skip_reason_label(
            "document_failed",
            error="报告详情页中未发现 PDF 链接。",
        )
        == "未发现 PDF 链接"
    )
    assert (
        get_skip_reason_label(
            "document_failed",
            error="报告页数不足：10 页，要求至少 20 页。",
        )
        == "PDF 页数不足"
    )


def test_get_candidate_status_label_returns_chinese_label() -> None:
    assert get_candidate_status_label("saved") == "已入库"
    assert get_candidate_status_label("pending_relevance") == "待授权"


def test_get_content_kind_label_returns_chinese_label() -> None:
    assert get_content_kind_label("pdf") == "PDF 报告"
    assert get_content_kind_label("web_article") == "网页长文"
    assert get_content_kind_label(None) == "未知类型"


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
    assert candidate.skip_reason_label == "PDF 页数不足"
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


@pytest.fixture
def legacy_short_pdf_candidate():
    return SimpleNamespace(
        id=1,
        crawl_run_id=2,
        source_id=3,
        report_id=None,
        title="Short PDF",
        url="https://example.org/report",
        normalized_url="https://example.org/report",
        status="skipped",
        skip_reason_code="document_failed",
        skip_reason_label="PDF 获取或页数/文本检查失败",
        error="报告页数不足：10 页，要求至少 20 页。",
        relevance=None,
        relevance_reason=None,
        is_china_related=None,
        pdf_url=None,
        page_count=None,
        non_empty_page_count=None,
        pdf_byte_length=None,
        content_kind=None,
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )


def test_to_read_relabels_legacy_document_failure(legacy_short_pdf_candidate) -> None:
    service = CrawlCandidateService()
    candidate = legacy_short_pdf_candidate
    response = service._to_read(candidate)

    assert response.skip_reason_label == "PDF 页数不足"
    assert response.page_count == 10
    assert response.content_kind == "pdf"
    assert candidate.page_count is None
    assert candidate.content_kind is None


@pytest.mark.parametrize(
    ("reason_code", "error"),
    [
        ("document_failed", "报告详情页中未发现 PDF 链接。"),
        ("document_failed", "报告页数不足"),
        ("document_failed", "报告页数不足：0 页，要求至少 20 页。"),
        ("document_failed", "报告页数不足：25 页，要求至少 20 页。"),
        ("document_failed", "HTTP 403: PDF 获取失败"),
        ("duplicate_existing", "报告页数不足：10 页，要求至少 20 页。"),
    ],
)
def test_legacy_metadata_requires_explicit_valid_page_check(
    legacy_short_pdf_candidate,
    reason_code: str,
    error: str,
) -> None:
    candidate = legacy_short_pdf_candidate
    candidate.skip_reason_code = reason_code
    candidate.error = error

    response = CrawlCandidateService()._to_read(candidate)

    assert response.page_count is None
    assert response.content_kind is None


def test_legacy_display_keeps_existing_metadata(legacy_short_pdf_candidate) -> None:
    candidate = legacy_short_pdf_candidate
    candidate.page_count = 12
    candidate.content_kind = "pdf"

    response = CrawlCandidateService()._to_read(candidate)

    assert response.page_count == 12
    assert response.content_kind == "pdf"


def test_mark_skipped_preserves_validated_pdf_metadata(legacy_short_pdf_candidate) -> None:
    candidate = legacy_short_pdf_candidate
    document = ReportDocumentResult(
        page_url=candidate.url,
        pdf_url="https://example.org/report.pdf",
        text="China policy report",
        page_count=14,
        non_empty_page_count=13,
        pdf_byte_length=1234,
    )

    mark_candidate_skipped(
        candidate,
        reason_code="document_failed",
        error=ReportDocumentValidationError(
            "报告页数不足：14 页，要求至少 20 页。",
            document=document,
        ),
    )

    assert candidate.status == "skipped"
    assert candidate.skip_reason_label == "PDF 页数不足"
    assert candidate.pdf_url == document.pdf_url
    assert candidate.page_count == 14
    assert candidate.non_empty_page_count == 13
    assert candidate.pdf_byte_length == 1234
    assert candidate.content_kind == "pdf"
    assert candidate.report_id is None


async def test_csv_uses_same_legacy_metadata_as_candidate_list(
    legacy_short_pdf_candidate,
) -> None:
    result = MagicMock()
    result.scalars.return_value.all.return_value = [legacy_short_pdf_candidate]
    db = SimpleNamespace(execute=AsyncMock(return_value=result))

    csv_text = await CrawlCandidateService().build_csv(db)
    rows = list(csv.DictReader(StringIO(csv_text.lstrip("\ufeff"))))

    assert rows[0]["内容类型"] == "pdf"
    assert rows[0]["页数"] == "10"
    assert rows[0]["PDF URL"] == ""
    assert rows[0]["非空页数"] == ""
    assert legacy_short_pdf_candidate.page_count is None


async def test_statistics_uses_same_legacy_pdf_type_as_candidate_list() -> None:
    status_result = MagicMock()
    status_result.all.return_value = [("skipped", 3)]
    reason_result = MagicMock()
    reason_result.all.return_value = [
        ("document_failed", None, "报告页数不足：10 页，要求至少 20 页。", None, None),
        ("document_failed", None, "报告详情页中未发现 PDF 链接。", None, None),
        ("duplicate_existing", None, None, None, None),
    ]
    kind_result = MagicMock()
    kind_result.all.return_value = [(None, 3)]
    db = SimpleNamespace(
        scalar=AsyncMock(return_value=3),
        execute=AsyncMock(side_effect=[status_result, reason_result, kind_result]),
    )

    statistics = await CrawlCandidateService().get_statistics(db)

    assert statistics.total == 3
    assert {item.code: item.count for item in statistics.by_content_kind} == {
        None: 2,
        "pdf": 1,
    }
    assert {item.label: item.count for item in statistics.by_skip_reason} == {
        "PDF 页数不足": 1,
        "未发现 PDF 链接": 1,
        "已入库重复": 1,
    }


@pytest.mark.parametrize("title", [None, "China report", "涉华报告"])
def test_document_metadata_binds_candidate_title_and_content(title) -> None:
    candidate = SimpleNamespace(title=title)
    document = ReportDocumentResult(
        page_url="https://example.org/report",
        pdf_url="https://example.org/report.pdf",
        text="报告正文\nChina policy",
        page_count=24,
        non_empty_page_count=23,
        pdf_byte_length=1234,
    )

    set_candidate_document_metadata(candidate, document)

    assert candidate.document_hash == document_hash(title or "", document.text)
    assert candidate.content_length == len(document.text)
    assert candidate.pdf_url == document.pdf_url
    assert candidate.page_count == 24
    assert not hasattr(candidate, "content")


def test_pending_relevance_clears_old_verdict_and_skip_reason(
    legacy_short_pdf_candidate,
) -> None:
    candidate = legacy_short_pdf_candidate
    candidate.relevance = "unrelated"
    candidate.relevance_reason = "Old verdict"
    candidate.is_china_related = False
    candidate.document_hash = "a" * 64
    candidate.content_length = 1000

    mark_candidate_pending_relevance(candidate, error=LLMNotAuthorized("Grant required"))

    assert candidate.status == "pending_relevance"
    assert candidate.skip_reason_code is None
    assert candidate.skip_reason_label is None
    assert candidate.relevance is None
    assert candidate.relevance_reason is None
    assert candidate.is_china_related is None
    assert candidate.error == "Grant required"
    assert candidate.document_hash == "a" * 64
    assert candidate.content_length == 1000
    response = CrawlCandidateService()._to_read(candidate)
    assert response.model_dump(mode="json")["status"] == "pending_relevance"
    assert response.is_china_related is None


async def test_pending_relevance_list_filter_statistics_and_csv(
    legacy_short_pdf_candidate,
) -> None:
    candidate = legacy_short_pdf_candidate
    mark_candidate_pending_relevance(candidate, error=LLMNotAuthorized("Grant required"))
    service = CrawlCandidateService()
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = [candidate]
    db = SimpleNamespace(
        scalar=AsyncMock(return_value=1),
        execute=AsyncMock(return_value=rows_result),
    )

    response = await service.get_recent_candidates(db, status="pending_relevance")
    assert response.total == 1
    assert response.items[0].status == "pending_relevance"
    list_query = db.execute.call_args.args[0].compile()
    assert "pending_relevance" in list_query.params.values()

    csv_text = await service.build_csv(db, status="pending_relevance")
    rows = list(csv.DictReader(StringIO(csv_text.lstrip("\ufeff"))))
    assert rows[0]["状态"] == "待授权"
    assert rows[0]["是否涉华"] == "未判断"
    assert rows[0]["跳过原因代码"] == ""
    assert rows[0]["跳过原因"] == ""
    csv_query = db.execute.call_args.args[0].compile()
    assert "pending_relevance" in csv_query.params.values()

    status_result = MagicMock()
    status_result.all.return_value = [("pending_relevance", 1)]
    reason_result = MagicMock()
    reason_result.all.return_value = []
    kind_result = MagicMock()
    kind_result.all.return_value = [(None, 1)]
    db.execute.side_effect = [status_result, reason_result, kind_result]
    statistics = await service.get_statistics(db)
    assert [(item.code, item.label, item.count) for item in statistics.by_status] == [
        ("pending_relevance", "待授权", 1),
    ]
    assert statistics.by_skip_reason == []
