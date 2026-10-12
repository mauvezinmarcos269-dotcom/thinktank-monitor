import pytest

from app.services.crawler.http_client import FetchResult
from app.services.crawler.pdf_extractor import PdfExtractionResult
from app.services.crawler.report_document_service import (
    MIN_REPORT_PAGE_COUNT,
    MIN_WEB_ARTICLE_CONTENT_LENGTH,
    ReportDocumentValidationError,
    fetch_report_document,
)


def test_report_document_default_thresholds_match_confirmed_policy() -> None:
    assert MIN_REPORT_PAGE_COUNT == 20
    assert MIN_WEB_ARTICLE_CONTENT_LENGTH == 3000


@pytest.mark.asyncio
async def test_fetch_report_document_allows_long_web_article_fallback(
    monkeypatch,
) -> None:
    async def fake_fetch_resource(url: str, timeout_seconds: float = 60.0) -> FetchResult:
        return FetchResult(
            content=f"""
<html>
  <body>
    <article>
      <div class="article-content">
        <p>{"China policy analysis. " * 200}</p>
      </div>
    </article>
  </body>
</html>
""".encode(),
            content_type="text/html; charset=utf-8",
            final_url=url,
            status_code=200,
        )

    monkeypatch.setattr(
        "app.services.crawler.report_document_service.fetch_resource",
        fake_fetch_resource,
    )

    document = await fetch_report_document(
        "https://www.brookings.edu/articles/china-policy/",
        allow_web_article_fallback=True,
    )

    assert document.content_kind == "web_article"
    assert document.pdf_url is None
    assert document.page_count is None
    assert document.non_empty_page_count is None
    assert document.pdf_byte_length is None
    assert len(document.text) >= MIN_WEB_ARTICLE_CONTENT_LENGTH


@pytest.mark.asyncio
async def test_fetch_report_document_rejects_short_web_article_fallback(
    monkeypatch,
) -> None:
    async def fake_fetch_resource(url: str, timeout_seconds: float = 60.0) -> FetchResult:
        return FetchResult(
            content=b"""
<html>
  <body>
    <article>
      <div class="article-content">
        <p>China policy analysis.</p>
      </div>
    </article>
  </body>
</html>
""",
            content_type="text/html; charset=utf-8",
            final_url=url,
            status_code=200,
        )

    monkeypatch.setattr(
        "app.services.crawler.report_document_service.fetch_resource",
        fake_fetch_resource,
    )

    with pytest.raises(ValueError, match="报告详情页中未发现 PDF 链接"):
        await fetch_report_document(
            "https://www.brookings.edu/articles/short-china-policy/",
            allow_web_article_fallback=True,
        )


@pytest.mark.asyncio
async def test_fetch_report_document_keeps_web_article_fallback_disabled_by_default(
    monkeypatch,
) -> None:
    async def fake_fetch_resource(url: str, timeout_seconds: float = 60.0) -> FetchResult:
        return FetchResult(
            content=f"""
<html>
  <body>
    <article>
      <div class="article-content">
        <p>{"China policy analysis. " * 200}</p>
      </div>
    </article>
  </body>
</html>
""".encode(),
            content_type="text/html; charset=utf-8",
            final_url=url,
            status_code=200,
        )

    monkeypatch.setattr(
        "app.services.crawler.report_document_service.fetch_resource",
        fake_fetch_resource,
    )

    with pytest.raises(ValueError, match="报告详情页中未发现 PDF 链接"):
        await fetch_report_document(
            "https://www.brookings.edu/articles/china-policy/",
        )


@pytest.mark.asyncio
async def test_fetch_report_document_falls_back_to_web_article_when_pdf_is_short(
    monkeypatch,
) -> None:
    async def fake_fetch_resource(url: str, timeout_seconds: float = 60.0) -> FetchResult:
        if url.endswith(".pdf"):
            return FetchResult(
                content=b"%PDF short pdf",
                content_type="application/pdf",
                final_url=url,
                status_code=200,
            )

        return FetchResult(
            content=f"""
<html>
  <body>
    <a href="https://example.org/report.pdf">Download PDF</a>
    <article>
      <div class="article-content">
        <p>{"China outbound investment analysis. " * 160}</p>
      </div>
    </article>
  </body>
</html>
""".encode(),
            content_type="text/html; charset=utf-8",
            final_url=url,
            status_code=200,
        )

    class FakeExtraction:
        page_count = MIN_REPORT_PAGE_COUNT - 1
        non_empty_page_count = MIN_REPORT_PAGE_COUNT - 1
        text = "short pdf text"

    monkeypatch.setattr(
        "app.services.crawler.report_document_service.fetch_resource",
        fake_fetch_resource,
    )
    monkeypatch.setattr(
        "app.services.crawler.report_document_service.extract_pdf_text",
        lambda _content: FakeExtraction(),
    )

    document = await fetch_report_document(
        "https://www.aei.org/research-products/report/china-investment/",
        allow_web_article_fallback=True,
    )

    assert document.content_kind == "web_article"
    assert document.pdf_url is None
    assert document.page_count is None
    assert len(document.text) >= MIN_WEB_ARTICLE_CONTENT_LENGTH


@pytest.mark.asyncio
async def test_fetch_report_document_keeps_short_pdf_error_when_web_article_is_short(
    monkeypatch,
) -> None:
    async def fake_fetch_resource(url: str, timeout_seconds: float = 60.0) -> FetchResult:
        if url.endswith(".pdf"):
            return FetchResult(
                content=b"%PDF short pdf",
                content_type="application/pdf",
                final_url=url,
                status_code=200,
            )

        return FetchResult(
            content=b"""
<html>
  <body>
    <a href="https://example.org/report.pdf">Download PDF</a>
    <article>
      <div class="article-content">
        <p>Short China analysis.</p>
      </div>
    </article>
  </body>
</html>
""",
            content_type="text/html; charset=utf-8",
            final_url=url,
            status_code=200,
        )

    class FakeExtraction:
        page_count = MIN_REPORT_PAGE_COUNT - 1
        non_empty_page_count = MIN_REPORT_PAGE_COUNT - 1
        text = "short pdf text"

    monkeypatch.setattr(
        "app.services.crawler.report_document_service.fetch_resource",
        fake_fetch_resource,
    )
    monkeypatch.setattr(
        "app.services.crawler.report_document_service.extract_pdf_text",
        lambda _content: FakeExtraction(),
    )

    with pytest.raises(ValueError, match="报告页数不足"):
        await fetch_report_document(
            "https://www.aei.org/research-products/report/short-china-analysis/",
            allow_web_article_fallback=True,
        )


@pytest.mark.parametrize(
    ("page_count", "text", "expected_error"),
    [
        (14, "China policy report text", "报告页数不足"),
        (21, "", "PDF 未提取出有效文本"),
    ],
)
async def test_document_validation_error_preserves_extracted_pdf_metadata(
    monkeypatch,
    page_count: int,
    text: str,
    expected_error: str,
) -> None:
    page_url = "https://example.org/reports/china"
    pdf_url = "https://example.org/files/china-final.pdf"
    pdf_bytes = b"%PDF validation test"
    non_empty_page_count = page_count - 1 if text else 0

    async def fake_fetch_resource(url: str) -> FetchResult:
        if url == page_url:
            return FetchResult(
                content=b'<a href="/download.pdf">Download PDF</a>',
                content_type="text/html",
                final_url=page_url,
                status_code=200,
            )

        assert url == "https://example.org/download.pdf"
        return FetchResult(
            content=pdf_bytes,
            content_type="application/pdf",
            final_url=pdf_url,
            status_code=200,
        )

    monkeypatch.setattr(
        "app.services.crawler.report_document_service.fetch_resource",
        fake_fetch_resource,
    )
    monkeypatch.setattr(
        "app.services.crawler.report_document_service.extract_pdf_text",
        lambda _content: PdfExtractionResult(
            text=text,
            page_count=page_count,
            non_empty_page_count=non_empty_page_count,
        ),
    )

    with pytest.raises(ReportDocumentValidationError, match=expected_error) as caught:
        await fetch_report_document(page_url)

    document = caught.value.document
    assert document.page_url == page_url
    assert document.pdf_url == pdf_url
    assert document.content_kind == "pdf"
    assert document.page_count == page_count
    assert document.non_empty_page_count == non_empty_page_count
    assert document.pdf_byte_length == len(pdf_bytes)
    assert document.text == text


async def test_document_at_minimum_page_count_still_passes(monkeypatch) -> None:
    pdf_bytes = b"%PDF valid report"
    pdf_url = "https://example.org/china.pdf"

    async def fake_fetch_resource(url: str) -> FetchResult:
        return FetchResult(
            content=pdf_bytes,
            content_type="application/pdf",
            final_url=url,
            status_code=200,
        )

    monkeypatch.setattr(
        "app.services.crawler.report_document_service.fetch_resource",
        fake_fetch_resource,
    )
    monkeypatch.setattr(
        "app.services.crawler.report_document_service.extract_pdf_text",
        lambda _content: PdfExtractionResult(
            text="China policy report text",
            page_count=MIN_REPORT_PAGE_COUNT,
            non_empty_page_count=MIN_REPORT_PAGE_COUNT,
        ),
    )

    document = await fetch_report_document(pdf_url)

    assert document.page_count == MIN_REPORT_PAGE_COUNT
    assert document.content_kind == "pdf"
    assert document.pdf_byte_length == len(pdf_bytes)
