from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.llm_authorization import LLMNotAuthorized, document_hash
from app.models import CrawlCandidate, CrawlRun, Report, Source, ThinkTank
from app.models.source import CrawlStatusEnum, SourceTypeEnum
from app.services import crawler_service
from app.services.crawl_quality_service import CrawlQualityStats
from app.services.crawler.report_document_service import ReportDocumentResult
from app.services.crawler_service import (
    _ensure_source_rollout_allowed,
    _fetch_source_articles,
    _is_source_due_for_crawl,
)


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


def test_source_rollout_guard_blocks_standard_review_source() -> None:
    with pytest.raises(
        ValueError,
        match="stage=standard_review",
    ):
        _ensure_source_rollout_allowed(
            source=SimpleNamespace(id=999),
            think_tank=SimpleNamespace(key="new_source"),
        )


def test_source_rollout_guard_allows_pilot_crawl_source() -> None:
    _ensure_source_rollout_allowed(
        source=SimpleNamespace(id=1),
        think_tank=SimpleNamespace(key="brookings"),
    )


def test_source_rollout_guard_allows_ecfr_after_policy_upgrade() -> None:
    _ensure_source_rollout_allowed(
        source=SimpleNamespace(id=21),
        think_tank=SimpleNamespace(key="ecfr"),
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
        (
            "https://www.chathamhouse.org/",
            "https://www.chathamhouse.org/2026/09/china-research-paper",
        ),
        (
            "https://ecfr.eu/",
            "https://ecfr.eu/publication/china-policy-brief/",
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
        "www.chathamhouse.org": """
<article>
  <a href="/2026/09/china-research-paper">
    Research paper China research paper
  </a>
  <time>17 September 2026</time>
</article>
""",
        "ecfr.eu": """
<article>
  <a href="/publication/china-policy-brief/">
    China policy brief
  </a>
  <span>Policy Brief</span>
  <time>17 September 2026</time>
</article>
""",
    }

    async def fake_fetch_resource(url: str, **_: object):
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


async def test_fetch_source_articles_skips_failed_core_site_discovery_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_fetch_resource(url: str, **_: object):
        if url == "https://www.aei.org/china-global-strategy/":
            raise RuntimeError("not found")

        html = ""
        if url == "https://www.aei.org/research-products/report/":
            html = """
<article>
  <a href="/research-products/report/china-competition">
    <h3>China competition report</h3>
  </a>
  <span>Report</span>
</article>
"""

        return SimpleNamespace(
            content=html.encode("utf-8"),
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
            url="https://www.aei.org/",
        )
    )

    assert [article["url"] for article in articles] == [
        "https://www.aei.org/research-products/report/china-competition"
    ]


async def test_fetch_source_articles_preflights_atlantic_council_pdf_links(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_fetch_resource(url: str, **_: object):
        html = ""

        if url == "https://www.atlanticcouncil.org/":
            html = """
<article>
  <a href="/in-depth-research-reports/report/china-no-pdf/">
    <h3>China no PDF report</h3>
  </a>
  <span>Report</span>
</article>
<article>
  <a href="/in-depth-research-reports/report/china-pdf/">
    <h3>China PDF report</h3>
  </a>
  <span>Report</span>
</article>
"""
        elif url == (
            "https://www.atlanticcouncil.org/in-depth-research-reports/"
            "report/china-no-pdf/"
        ):
            html = "<main><h1>China no PDF report</h1></main>"
        elif url == (
            "https://www.atlanticcouncil.org/in-depth-research-reports/"
            "report/china-pdf/"
        ):
            html = """
<main>
  <h1>China PDF report</h1>
  <a href="/wp-content/uploads/2026/10/china-pdf.pdf">Download PDF</a>
</main>
"""

        return SimpleNamespace(
            content=html.encode("utf-8"),
            final_url=url,
            content_type="text/html",
        )

    monkeypatch.setattr(
        crawler_service,
        "fetch_resource",
        fake_fetch_resource,
    )

    articles = await _fetch_source_articles(
        SimpleNamespace(
            source_type=SourceTypeEnum.website,
            url="https://www.atlanticcouncil.org/",
        )
    )

    assert articles[0]["preflight_skip_reason_code"] == "document_failed"
    assert articles[0]["preflight_skip_error"] == (
        "发现阶段预检：报告详情页中未发现 PDF 链接。"
    )
    assert articles[1]["pdf_url"] == (
        "https://www.atlanticcouncil.org/wp-content/uploads/2026/10/china-pdf.pdf"
    )


async def test_fetch_source_articles_uses_csis_analysis_discovery_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_fetch_resource(url: str, **_: object):
        html = ""
        if url == "https://www.csis.org/analysis":
            html = """
<article class="report-search-listing">
  <h3>
    <a href="/analysis/china-strategy-report">
      China Strategy Report
    </a>
  </h3>
  <span>Report — September 12, 2026</span>
</article>
"""

        return SimpleNamespace(
            content=html.encode("utf-8"),
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
            url="https://www.csis.org/",
        )
    )

    assert [article["url"] for article in articles] == [
        "https://www.csis.org/analysis/china-strategy-report",
    ]


async def test_fetch_source_articles_parses_current_csis_search_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_fetch_resource(url: str, **_: object):
        html = ""
        if url == "https://www.csis.org/analysis":
            html = """
<div class="views-row">
  <h3>
    <a href="/analysis/china-military-balance-report">
      China Military Balance Report
    </a>
  </h3>
  <div class="meta">Report by Sample Author — September 14, 2026</div>
</div>
<div class="views-row">
  <h3>
    <a href="/analysis/china-quick-take">
      China Quick Take
    </a>
  </h3>
  <div class="meta">Commentary by Sample Author — September 15, 2026</div>
</div>
"""

        return SimpleNamespace(
            content=html.encode("utf-8"),
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
            url="https://www.csis.org/",
        )
    )

    assert articles == [
        {
            "title": "China Military Balance Report",
            "url": "https://www.csis.org/analysis/china-military-balance-report",
            "published_at": datetime(2026, 9, 14),
            "content_type": "report",
        }
    ]


async def test_fetch_source_articles_filters_csis_report_search_listing_to_reports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_fetch_resource(url: str, **_: object):
        html = ""
        if url == "https://www.csis.org/analysis":
            html = """
<article class="report-search-listing">
  <h3>
    <a href="https://features.csis.org/hiddenreach/china-djibouti-base-upgrade">
      Extended Range: China Upgrades Its Military Base in Djibouti
    </a>
  </h3>
  <span>
    Digital Feature by Sample Author — September 17, 2026
  </span>
</article>
<article class="report-search-listing">
  <h3>
    <a href="/analysis/china-semiconductor-report">
      China Semiconductor Report
    </a>
  </h3>
  <span>Report by Sample Author — September 17, 2026</span>
</article>
"""

        return SimpleNamespace(
            content=html.encode("utf-8"),
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
            url="https://www.csis.org/",
        )
    )

    assert [article["url"] for article in articles] == [
        "https://www.csis.org/analysis/china-semiconductor-report",
    ]


async def test_fetch_source_articles_uses_csis_sitemap_pdf_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_fetch_resource(url: str, **_: object):
        html = ""

        if url == "https://www.csis.org/sitemap.xml":
            html = """
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://www.csis.org/sitemap.xml?page=1</loc>
  </sitemap>
</sitemapindex>
"""
        elif url == "https://www.csis.org/sitemap.xml?page=1":
            html = """
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://www.csis.org/analysis/china-russia-security-report</loc>
    <lastmod>2026-09-09T11:55:26-04:00</lastmod>
  </url>
  <url>
    <loc>https://www.csis.org/analysis/global-security-report</loc>
    <lastmod>2026-09-10T11:55:26-04:00</lastmod>
  </url>
</urlset>
"""
        elif url == "https://www.csis.org/analysis/china-russia-security-report":
            html = """
<article>
  <h1>China-Russia Security Report</h1>
  <a href="https://csis-website-prod.s3.amazonaws.com/report.pdf">
    Download PDF
  </a>
</article>
"""

        return SimpleNamespace(
            content=html.encode("utf-8"),
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
            url="https://www.csis.org/",
        )
    )

    assert articles == [
        {
            "title": "China-Russia Security Report",
            "url": "https://www.csis.org/analysis/china-russia-security-report",
            "published_at": datetime(2026, 9, 9, 11, 55, 26),
            "content_type": "report",
        }
    ]


async def test_fetch_source_articles_skips_failed_csis_discovery_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_fetch_resource(url: str, **_: object):
        if "content_type%3Areport" in url:
            raise RuntimeError("blocked")

        html = ""
        if url == "https://www.csis.org/regions/asia/china":
            html = """
<article class="search-result">
  <h2>
    <a href="/analysis/china-security-report">
      China Security Report
    </a>
  </h2>
  <span class="content-type">Report</span>
  <time datetime="2026-09-16T12:00:00-04:00">September 16, 2026</time>
</article>
"""

        return SimpleNamespace(
            content=html.encode("utf-8"),
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
            url="https://www.csis.org/",
        )
    )

    assert [article["url"] for article in articles] == [
        "https://www.csis.org/analysis/china-security-report",
    ]


async def test_fetch_source_articles_routes_nber_to_search_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_fetch_resource(url: str, **_: object):
        assert url == "https://www.nber.org/api/v1/search?q=China"
        content = """
{
  "results": [
    {
      "title": "The China Backlash",
      "type": "working_paper",
      "url": "/papers/w35539",
      "displaydate": "August 2026"
    }
  ]
}
"""
        return SimpleNamespace(
            content=content.encode("utf-8"),
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
            url="https://www.nber.org/",
        )
    )

    assert [article["url"] for article in articles] == [
        "https://www.nber.org/papers/w35539",
    ]


@pytest.mark.parametrize(
    ("outcome", "status", "skip_reason", "related"),
    [
        (LLMNotAuthorized("Outbound disabled"), "pending_relevance", None, None),
        (LLMNotAuthorized("Grant required"), "pending_relevance", None, None),
        (TimeoutError("Model timeout"), "skipped", "relevance_failed", None),
        (ValueError("Invalid model JSON"), "skipped", "relevance_failed", None),
        (
            {"relevance": "unrelated", "is_china_related": False, "reason": "Other topic"},
            "skipped",
            "non_china_related",
            False,
        ),
        (
            {"relevance": "direct", "is_china_related": True, "reason": "China policy"},
            "saved",
            None,
            True,
        ),
    ],
)
async def test_candidate_relevance_outcomes_remain_distinct(
    monkeypatch, outcome, status, skip_reason, related,
) -> None:
    source = SimpleNamespace(
        id=7,
        think_tank_id=7,
        is_active=True,
        source_type=SourceTypeEnum.website,
    )
    added = []

    def add(item):
        item.id = len(added) + 1
        added.append(item)

    def get(model, _id):
        if model is Source:
            return source
        if model is ThinkTank:
            return SimpleNamespace(key="rand")
        assert model is CrawlRun
        return next(item for item in added if isinstance(item, CrawlRun))

    db = MagicMock()
    db.__aenter__.return_value = db
    db.get = AsyncMock(side_effect=get)
    db.add.side_effect = add
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    monkeypatch.setattr(crawler_service, "AsyncSessionLocal", lambda: db)

    articles = [
        {"title": "T" * 510, "url": "https://example.org/report/#top", "published_at": None},
        {"title": "", "url": "https://example.org/another", "published_at": None},
    ]
    document = ReportDocumentResult(
        page_url=articles[0]["url"],
        pdf_url="https://example.org/report.pdf",
        text="China policy report",
        page_count=24,
        non_empty_page_count=23,
        pdf_byte_length=1234,
    )
    monkeypatch.setattr(crawler_service, "_fetch_source_articles", AsyncMock(return_value=articles))
    monkeypatch.setattr(crawler_service, "fetch_report_document", AsyncMock(return_value=document))
    evaluate = AsyncMock(side_effect=[outcome, LLMNotAuthorized("Grant required")])
    monkeypatch.setattr(crawler_service, "evaluate_china_relevance", evaluate)
    notify = AsyncMock()
    monkeypatch.setattr(crawler_service.notification_service, "create_for_all_active_users", notify)
    stats = CrawlQualityStats(raw_candidates=2)
    monkeypatch.setattr(crawler_service, "CrawlQualityStats", lambda **_kwargs: stats)

    response = await crawler_service._crawl_source_locked_async(7, only_if_due=False)

    candidates = [item for item in added if isinstance(item, CrawlCandidate)]
    assert len(candidates) == 2
    first, waiting = candidates
    assert first.status == status
    assert first.skip_reason_code == skip_reason
    assert first.is_china_related is related
    assert waiting.status == "pending_relevance"
    assert waiting.is_china_related is None
    assert waiting.relevance is None
    assert waiting.relevance_reason is None
    assert waiting.skip_reason_code is None
    assert waiting.skip_reason_label is None
    assert waiting.error == "Grant required"
    assert first.title == "T" * 500
    assert evaluate.await_count == 2
    for candidate, call in zip(candidates, evaluate.await_args_list, strict=True):
        assert call.args == (candidate.title or "", document.text)
        assert call.kwargs == {"source_id": source.id, "normalized_url": candidate.normalized_url}
        assert candidate.document_hash == document_hash(*call.args)
        assert candidate.content_length == len(document.text)
        assert candidate.page_count == 24

    saved_count = int(status == "saved")
    reports = [item for item in added if isinstance(item, Report)]
    assert len(reports) == saved_count
    assert notify.await_count == saved_count
    assert response == {
        "status": "success", "source_id": 7, "found_count": 2, "saved_count": saved_count,
    }
    run = next(item for item in added if isinstance(item, CrawlRun))
    assert run.status == "success"
    assert run.finished_at is not None
    assert source.last_crawl_status == CrawlStatusEnum.success
    assert source.last_error is None
    assert db.commit.await_count == 2
    assert stats.pending_relevance == 1 + int(status == "pending_relevance")
    assert stats.relevance_failed == int(skip_reason == "relevance_failed")
    assert stats.non_china_related == int(skip_reason == "non_china_related")
    assert stats.document_failed == 0
    assert f"待授权 {stats.pending_relevance} 条" in run.error
    if status == "pending_relevance":
        assert first.error == str(outcome)
        assert first.skip_reason_label is None
        assert first.relevance is None
        assert first.relevance_reason is None
        assert "失败" not in run.error
        assert "非涉华" not in run.error
        assert "跳过" not in run.error
