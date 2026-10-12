from datetime import datetime

from app.services.crawler.ecfr_parser import parse_ecfr_reports


def test_parse_ecfr_reports_extracts_policy_briefs_on_china_topic() -> None:
    html = """
<article>
  <a href="https://ecfr.eu/publication/the-art-of-the-swarm-systemic-rivalry-with-china-on-european-terms/">
    The art of the swarm: Systemic rivalry with China on European terms
  </a>
  <span>Andrew Small</span>
  <span>Policy Brief</span>
  <time>17 June 2026</time>
  <p>The EU can exploit its system to say no to China.</p>
</article>
<article>
  <a href="https://ecfr.eu/article/a-future-with-chinese-characteristics/">
    A future with Chinese characteristics
  </a>
  <span>Commentary</span>
</article>
<article>
  <a href="https://ecfr.eu/podcasts/episode/germanys-second-china-shock/">
    Germany's second China shock
  </a>
  <span>Podcast</span>
</article>
"""

    articles = parse_ecfr_reports(
        html,
        "https://ecfr.eu/topic/china/",
    )

    assert articles == [
        {
            "title": "The art of the swarm: Systemic rivalry with China on European terms",
            "url": (
                "https://ecfr.eu/publication/"
                "the-art-of-the-swarm-systemic-rivalry-with-china-on-european-terms/"
            ),
            "published_at": datetime(2026, 6, 17),
            "content_type": "policy_brief",
            "allow_web_article_fallback": True,
        }
    ]


def test_parse_ecfr_reports_requires_china_signal_outside_china_topic() -> None:
    html = """
<article>
  <a href="/publication/life-of-the-party-democrats-and-the-search-for-a-post-trump-future/">
    Life of the party: Democrats and the search for a post-Trump future
  </a>
  <span>Policy Brief</span>
  <time>15 September 2026</time>
</article>
<article>
  <a href="/publication/beijing-holdem-european-cards-against-chinese-coercion/">
    Beijing hold’em: European cards against Chinese coercion
  </a>
  <span>Policy Brief</span>
  <time>31 March 2026</time>
</article>
"""

    articles = parse_ecfr_reports(
        html,
        "https://ecfr.eu/publications/",
    )

    assert [article["title"] for article in articles] == [
        "Beijing hold’em: European cards against Chinese coercion"
    ]
