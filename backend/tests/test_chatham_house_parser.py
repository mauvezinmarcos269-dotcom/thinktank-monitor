from datetime import datetime

from app.services.crawler.chatham_house_parser import parse_chatham_house_reports


def test_parse_chatham_house_reports_extracts_china_report_cards() -> None:
    html = """
<article>
  <a href="/2026/09/china-weathering-hormuz-energy-crisis-copying-its-model-comes-risks">
    Expert comment China is weathering the Hormuz energy crisis. But copying its model comes with risks
  </a>
  <p>China absorbed the shock by drawing on stockpiles.</p>
  <time>18 September 2026</time>
</article>
<article>
  <a href="/2026/09/how-uk-should-protect-its-science-and-tech-research-foreign-state-threats">
    Research paper How the UK should protect its science and tech research from foreign state threats
  </a>
  <p>The UK university system thrives on openness.</p>
  <time>17 September 2026</time>
</article>
<article>
  <a href="/2026/09/research-paper-china-technology-security">
    Research paper China technology security report
  </a>
  <time>16 September 2026</time>
</article>
"""

    articles = parse_chatham_house_reports(
        html,
        "https://www.chathamhouse.org/",
    )

    assert articles == [
        {
            "title": "China technology security report",
            "url": (
                "https://www.chathamhouse.org/2026/09/"
                "research-paper-china-technology-security"
            ),
            "published_at": datetime(2026, 9, 16),
            "content_type": "research_report",
            "allow_web_article_fallback": True,
        }
    ]


def test_parse_chatham_house_reports_keeps_reports_on_china_context_page() -> None:
    html = """
<article>
  <a href="/2026/09/how-uk-should-protect-its-science-and-tech-research-foreign-state-threats">
    Research paper How the UK should protect its science and tech research from foreign state threats
  </a>
  <time>17 September 2026</time>
</article>
"""

    articles = parse_chatham_house_reports(
        html,
        "https://www.chathamhouse.org/research/regions/asia-pacific/china",
    )

    assert [article["title"] for article in articles] == [
        "How the UK should protect its science and tech research from foreign state threats"
    ]
