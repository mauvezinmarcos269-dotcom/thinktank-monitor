import pytest

from app.services.crawler.rss_parser import parse_rss_articles


def test_parse_rss_articles_recovers_from_undefined_html_entities() -> None:
    feed_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example</title>
    <item>
      <title>China &mdash; policy brief</title>
      <link>/research/china-policy-brief</link>
      <description>Trade&nbsp;analysis with &ldquo;quotes&rdquo;.</description>
      <pubDate>Mon, 07 Sep 2026 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

    articles = parse_rss_articles(feed_content, "https://example.org/feed/")

    assert articles == [
        {
            "title": "China — policy brief",
            "url": "https://example.org/research/china-policy-brief",
            "content": "Trade analysis with “quotes”.",
            "published_at": articles[0]["published_at"],
        }
    ]
    assert articles[0]["published_at"] is not None


def test_parse_rss_articles_rejects_html_page_response() -> None:
    feed_content = b"""<!DOCTYPE html>
<html lang="en">
  <head><title>Not an RSS feed</title></head>
  <body>Homepage</body>
</html>
"""

    with pytest.raises(ValueError, match="来源返回 HTML 页面"):
        parse_rss_articles(feed_content, "https://example.org/feed/")
