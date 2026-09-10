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


def test_parse_rss_articles_escapes_bare_ampersands_in_links() -> None:
    feed_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example</title>
    <item>
      <title>China trade report</title>
      <link>https://example.org/report?topic=china&format=pdf</link>
      <description>Long report</description>
    </item>
  </channel>
</rss>
"""

    articles = parse_rss_articles(feed_content, "https://example.org/feed/")

    assert articles[0]["url"] == "https://example.org/report?topic=china&format=pdf"


def test_parse_rss_articles_preserves_unknown_named_entities_as_text() -> None:
    feed_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example</title>
    <item>
      <title>China &madeup; research</title>
      <link>/research/china</link>
      <description>Contains a custom entity.</description>
    </item>
  </channel>
</rss>
"""

    articles = parse_rss_articles(feed_content, "https://example.org/feed/")

    assert articles[0]["title"] == "China &madeup research"


def test_parse_rss_articles_removes_invalid_xml_control_characters() -> None:
    feed_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example</title>
    <item>
      <title>China\x08 strategy report</title>
      <link>/research/china-strategy</link>
      <description>Report text</description>
    </item>
  </channel>
</rss>
"""

    articles = parse_rss_articles(feed_content, "https://example.org/feed/")

    assert articles[0]["title"] == "China strategy report"
