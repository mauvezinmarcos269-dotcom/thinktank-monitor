from datetime import datetime

from app.services.crawler.brookings_parser import parse_brookings_reports


def test_parse_brookings_reports_extracts_article_cards() -> None:
    html = """
<article class="article">
  <a href="https://www.brookings.edu/articles/europes-china-shock-2-0/"
     class="overlay-link">
    <span class="sr-only">Europe's China Shock 2.0</span>
  </a>
  <div class="article-insert">
    <span class="article-title">Europe's China Shock 2.0</span>
    <span class="meta"><p class="date">September 9, 2026</p></span>
  </div>
</article>
<article class="article">
  <a href="/regions/asia-the-pacific/china/" class="overlay-link">
    <span class="sr-only">China</span>
  </a>
  <span class="article-title">China</span>
</article>
<article class="article">
  <a href="/reports/sample-china-report/" class="overlay-link">
    <span class="sr-only">Sample China report</span>
  </a>
  <span class="article-title">Sample China report</span>
</article>
<article class="article">
  <a href="/reports/sample-china-report/" class="overlay-link">
    <span class="sr-only">Sample China report duplicate</span>
  </a>
</article>
"""

    articles = parse_brookings_reports(
        html,
        "https://www.brookings.edu/regions/asia-the-pacific/china/",
    )

    assert articles == [
        {
            "title": "Europe's China Shock 2.0",
            "url": "https://www.brookings.edu/articles/europes-china-shock-2-0/",
            "published_at": datetime(2026, 9, 9),
            "content_type": "web_article",
            "allow_web_article_fallback": True,
        },
        {
            "title": "Sample China report",
            "url": "https://www.brookings.edu/reports/sample-china-report/",
            "published_at": None,
            "content_type": "report",
            "allow_web_article_fallback": False,
        },
    ]


def test_parse_brookings_reports_filters_generic_homepage_articles() -> None:
    html = """
<article class="article">
  <a href="/articles/local-employment-in-2026/" class="overlay-link">
    <span class="sr-only">Local employment in 2026</span>
  </a>
  <span class="article-title">Local employment in 2026</span>
</article>
<article class="article">
  <a href="/articles/a-summer-of-ai-summits-reveals-a-widening-us-china-divide/"
     class="overlay-link">
    <span class="sr-only">A summer of AI summits reveals a widening US-China divide</span>
  </a>
  <span class="article-title">A summer of AI summits reveals a widening US-China divide</span>
</article>
<article class="article">
  <a href="/reports/global-economic-outlook/" class="overlay-link">
    <span class="sr-only">Global economic outlook</span>
  </a>
  <span class="article-title">Global economic outlook</span>
</article>
"""

    articles = parse_brookings_reports(
        html,
        "https://www.brookings.edu/",
    )

    assert [article["title"] for article in articles] == [
        "A summer of AI summits reveals a widening US-China divide",
        "Global economic outlook",
    ]
    assert articles[0]["allow_web_article_fallback"] is True
    assert articles[1]["allow_web_article_fallback"] is False


def test_parse_brookings_reports_keeps_articles_on_china_topic_page() -> None:
    html = """
<article class="article">
  <a href="/articles/turning-the-tide/" class="overlay-link">
    <span class="sr-only">Turning the tide</span>
  </a>
  <span class="article-title">Turning the tide</span>
</article>
"""

    articles = parse_brookings_reports(
        html,
        "https://www.brookings.edu/regions/asia-the-pacific/china/",
    )

    assert [article["title"] for article in articles] == [
        "Turning the tide",
    ]
