from datetime import datetime

from app.services.crawler.cap_parser import parse_cap_reports


def test_parse_cap_reports_keeps_report_cards_on_china_page() -> None:
    html = """
<article>
  <a href="/article/china-industrial-policy-report/">
    <h3>Industrial Policy Choices</h3>
  </a>
  <p>Report September 10, 2026</p>
</article>
<article>
  <a href="/article/china-news-analysis/">
    <h3>China News Analysis</h3>
  </a>
  <p>Article August 3, 2026</p>
</article>
"""

    articles = parse_cap_reports(
        html,
        "https://www.americanprogress.org/topic/china/",
    )

    assert articles == [
        {
            "title": "Industrial Policy Choices",
            "url": (
                "https://www.americanprogress.org/article/"
                "china-industrial-policy-report/"
            ),
            "published_at": datetime(2026, 9, 10),
            "content_type": "report",
            "allow_web_article_fallback": True,
        }
    ]


def test_parse_cap_reports_requires_china_signal_off_general_pages() -> None:
    html = """
<article>
  <a href="/article/climate-policy-report/">
    <h3>Climate Policy Report</h3>
  </a>
  <p>Report September 10, 2026</p>
</article>
<article>
  <a href="/article/china-clean-energy-report/">
    <h3>China Clean Energy Report</h3>
  </a>
  <p>Report September 11, 2026</p>
</article>
"""

    articles = parse_cap_reports(
        html,
        "https://www.americanprogress.org/",
    )

    assert [article["title"] for article in articles] == [
        "China Clean Energy Report",
    ]


def test_parse_cap_reports_ignores_non_cap_urls() -> None:
    html = """
<article>
  <a href="https://example.org/article/china-report/">
    <h3>China Report</h3>
  </a>
  <p>Report September 10, 2026</p>
</article>
"""

    assert parse_cap_reports(
        html,
        "https://www.americanprogress.org/topic/china/",
    ) == []
