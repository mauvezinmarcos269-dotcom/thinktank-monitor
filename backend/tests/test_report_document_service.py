import pytest

from app.services.crawler.http_client import FetchResult
from app.services.crawler.report_document_service import fetch_report_document


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
    assert len(document.text) >= 3000


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
