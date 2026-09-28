from app.models.source import CrawlStatusEnum
from app.services.source_diagnosis_service import classify_source_diagnosis


def test_classifies_http_status_error() -> None:
    diagnosis = classify_source_diagnosis(
        crawl_status=CrawlStatusEnum.failed,
        error_text="HTTPStatusError: Client error '403 Forbidden'",
        saved_report_count=0,
    )

    assert diagnosis.code == "http_status"


def test_classifies_short_pdf_error() -> None:
    diagnosis = classify_source_diagnosis(
        crawl_status=CrawlStatusEnum.failed,
        error_text="ValueError: 报告页数不足：12 页，要求至少 20 页。",
        saved_report_count=0,
    )

    assert diagnosis.code == "short_pdf"


def test_classifies_missing_parser_error() -> None:
    diagnosis = classify_source_diagnosis(
        crawl_status=CrawlStatusEnum.failed,
        error_text="ValueError: 当前尚未配置该 website 来源的专用解析器",
        saved_report_count=0,
    )

    assert diagnosis.code == "parser"


def test_classifies_success_without_reports() -> None:
    diagnosis = classify_source_diagnosis(
        crawl_status=CrawlStatusEnum.success,
        error_text=None,
        saved_report_count=0,
    )

    assert diagnosis.code == "no_reports_saved"


def test_classifies_success_without_candidates_from_quality_summary() -> None:
    diagnosis = classify_source_diagnosis(
        crawl_status=CrawlStatusEnum.success,
        error_text="质量检查：原始候选 0 条；有效去重后 0 条；入库 0 条",
        saved_report_count=0,
    )

    assert diagnosis.code == "no_candidates"


def test_classifies_success_without_reports_due_to_document_gate() -> None:
    diagnosis = classify_source_diagnosis(
        crawl_status=CrawlStatusEnum.success,
        error_text="质量检查：原始候选 4 条；有效去重后 4 条；入库 0 条；跳过：PDF 获取或页数/文本检查失败 4 条",
        saved_report_count=0,
    )

    assert diagnosis.code == "document_gate_failed"


def test_classifies_success_without_reports_due_to_non_china_candidates() -> None:
    diagnosis = classify_source_diagnosis(
        crawl_status=CrawlStatusEnum.success,
        error_text="质量检查：原始候选 3 条；有效去重后 3 条；入库 0 条；跳过：非涉华 3 条",
        saved_report_count=0,
    )

    assert diagnosis.code == "non_china_candidates"


def test_classifies_success_without_reports_due_to_duplicates() -> None:
    diagnosis = classify_source_diagnosis(
        crawl_status=CrawlStatusEnum.success,
        error_text="质量检查：原始候选 2 条；有效去重后 2 条；入库 0 条；跳过：已入库重复 2 条",
        saved_report_count=0,
    )

    assert diagnosis.code == "duplicate_candidates"
