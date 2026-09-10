from datetime import datetime

from app.services.crawler.report_candidate_filter import is_heavy_report_candidate
from app.services.crawler.us_core_parser import (
    CORE_SITE_CONFIGS,
    parse_core_site_reports,
)


def test_heavy_report_filter_rejects_lightweight_content() -> None:
    assert not is_heavy_report_candidate(
        title="Podcast: China and global trade",
        url="https://example.org/podcast/china-trade",
        text="Podcast episode",
        content_type="report",
    )


def test_heavy_report_filter_keeps_report_style_content() -> None:
    assert is_heavy_report_candidate(
        title="China policy report",
        url="https://example.org/reports/china-policy-report",
        text="A long research report",
        content_type="report",
    )


def test_parse_rand_reports_extracts_research_publications() -> None:
    html = """
<article>
  <a href="/pubs/research_reports/RRA123-1.html">
    <h3>China's Military Modernization</h3>
  </a>
  <span>Research Report</span>
  <time>September 8, 2026</time>
</article>
<article>
  <a href="/blog/2026/china-commentary.html">
    <h3>China commentary</h3>
  </a>
  <span>Commentary</span>
</article>
"""

    articles = parse_core_site_reports(
        html,
        "https://www.rand.org/pubs.html",
        CORE_SITE_CONFIGS["rand"],
    )

    assert articles == [
        {
            "title": "China's Military Modernization",
            "url": "https://www.rand.org/pubs/research_reports/RRA123-1.html",
            "published_at": datetime(2026, 9, 8),
            "content_type": "research_report",
            "allow_web_article_fallback": False,
        }
    ]


def test_parse_cfr_reports_filters_to_report_paths() -> None:
    html = """
<li>
  <a href="/report/china-strategy-2026">
    <h2>China Strategy 2026</h2>
  </a>
  <span>Report</span>
  <span>September 7, 2026</span>
</li>
<li>
  <a href="/in-brief/china-news">
    <h2>China news brief</h2>
  </a>
</li>
"""

    articles = parse_core_site_reports(
        html,
        "https://www.cfr.org/report",
        CORE_SITE_CONFIGS["cfr"],
    )

    assert [article["url"] for article in articles] == [
        "https://www.cfr.org/report/china-strategy-2026",
    ]


def test_parse_china_context_page_keeps_piiE_publications_without_title_signal() -> None:
    html = """
<div class="publication-card">
  <a href="/research/publications/supply-chain-policy">
    <h3>Supply chain policy choices</h3>
  </a>
  <span>Working Paper</span>
  <span>8 September 2026</span>
</div>
"""

    articles = parse_core_site_reports(
        html,
        "https://www.piie.com/research/china",
        CORE_SITE_CONFIGS["piie"],
    )

    assert articles[0]["title"] == "Supply chain policy choices"
    assert articles[0]["published_at"] == datetime(2026, 9, 8)


def test_parse_carnegie_requires_china_signal_off_general_page() -> None:
    html = """
<article>
  <a href="/research/2026/09/global-energy-report">
    <h3>Global energy report</h3>
  </a>
  <span>Report</span>
</article>
<article>
  <a href="/research/2026/09/china-and-global-energy">
    <h3>China and global energy</h3>
  </a>
  <span>Report</span>
</article>
"""

    articles = parse_core_site_reports(
        html,
        "https://carnegieendowment.org/research?lang=en",
        CORE_SITE_CONFIGS["carnegie"],
    )

    assert [article["title"] for article in articles] == [
        "China and global energy",
    ]
