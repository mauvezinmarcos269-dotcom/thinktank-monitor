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
