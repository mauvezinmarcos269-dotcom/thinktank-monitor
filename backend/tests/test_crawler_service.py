from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.models.source import SourceTypeEnum
from app.services import crawler_service
from app.services.crawler_service import _fetch_source_articles, _is_source_due_for_crawl


def make_source(
    *,
    last_crawled_at,
    crawl_frequency_minutes: int = 1440,
):
    return SimpleNamespace(
        last_crawled_at=last_crawled_at,
        crawl_frequency_minutes=crawl_frequency_minutes,
    )


def test_source_without_last_crawl_is_due() -> None:
    now = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)

    assert _is_source_due_for_crawl(
        make_source(last_crawled_at=None),
        now=now,
    )


def test_source_is_not_due_before_frequency_window() -> None:
    now = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)

    assert not _is_source_due_for_crawl(
        make_source(
            last_crawled_at=now - timedelta(minutes=30),
            crawl_frequency_minutes=60,
        ),
        now=now,
    )


def test_source_is_due_after_frequency_window() -> None:
    now = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)

    assert _is_source_due_for_crawl(
        make_source(
            last_crawled_at=now - timedelta(minutes=61),
            crawl_frequency_minutes=60,
        ),
        now=now,
    )


def test_source_due_check_accepts_naive_database_time() -> None:
    now = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
    naive_last_crawled_at = datetime(2026, 9, 7, 10, 59)

    assert _is_source_due_for_crawl(
        make_source(
            last_crawled_at=naive_last_crawled_at,
            crawl_frequency_minutes=60,
        ),
        now=now,
    )


@pytest.mark.parametrize(
    ("source_url", "expected_url"),
    [
        (
            "https://www.rand.org/",
            "https://www.rand.org/pubs/research_reports/RRA123-1.html",
        ),
        (
            "https://carnegieendowment.org/",
            "https://carnegieendowment.org/research/2026/09/china-report",
        ),
        (
            "https://www.cfr.org/",
            "https://www.cfr.org/report/china-strategy",
        ),
        (
            "https://www.piie.com/",
            "https://www.piie.com/research/publications/china-trade",
        ),
    ],
)
async def test_fetch_source_articles_routes_core_us_sites(
    monkeypatch: pytest.MonkeyPatch,
    source_url: str,
    expected_url: str,
) -> None:
    html_by_host = {
        "www.rand.org": """
<article>
  <a href="/pubs/research_reports/RRA123-1.html">
    <h3>China report</h3>
  </a>
  <span>Research Report</span>
</article>
""",
        "carnegieendowment.org": """
<article>
  <a href="/research/2026/09/china-report">
    <h3>China report</h3>
  </a>
  <span>Report</span>
</article>
""",
        "www.cfr.org": """
<article>
  <a href="/report/china-strategy">
    <h3>China strategy</h3>
  </a>
  <span>Report</span>
</article>
""",
        "www.piie.com": """
<article>
  <a href="/research/publications/china-trade">
    <h3>China trade report</h3>
  </a>
  <span>Working Paper</span>
</article>
""",
    }

    async def fake_fetch_resource(url: str):
        from urllib.parse import urlsplit

        hostname = urlsplit(url).netloc.lower()
        return SimpleNamespace(
            content=html_by_host.get(hostname, "").encode("utf-8"),
            final_url=url,
        )

    monkeypatch.setattr(
        crawler_service,
        "fetch_resource",
        fake_fetch_resource,
    )

    articles = await _fetch_source_articles(
        SimpleNamespace(
            source_type=SourceTypeEnum.website,
            url=source_url,
        )
    )

    assert [article["url"] for article in articles] == [expected_url]
