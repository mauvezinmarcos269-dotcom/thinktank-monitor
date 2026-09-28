from datetime import datetime

from app.services.crawler.report_candidate_filter import (
    has_china_signal,
    is_heavy_report_candidate,
)
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


def test_china_signal_requires_word_boundaries_for_short_acronyms() -> None:
    assert has_china_signal(
        title="PLA modernization report",
        url="https://example.org/report/pla-modernization",
    )
    assert has_china_signal(
        title="Countering CCP influence operations",
        url="https://example.org/report/countering-ccp-influence",
    )
    assert not has_china_signal(
        title="Making the Varsity Cut: Who Plays High School Sports",
        url="https://example.org/report/making-the-varsity-cut",
    )
    assert not has_china_signal(
        title="The Marketplace of Ideas",
        url="https://example.org/report/marketplace-of-ideas",
    )
    assert not has_china_signal(
        title="Acceptance and public trust",
        url="https://example.org/report/acceptance-and-public-trust",
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


def test_parse_rand_reports_requires_china_signal_in_title_or_url() -> None:
    html = """
<article>
  <a href="/pubs/perspectives/PEA4593-1.html">
    <h3>Understanding Russia's Role in Latin America</h3>
  </a>
  <p>BRICS members include China, but the report is about Russia.</p>
  <span>Research Report</span>
</article>
<article>
  <a href="/pubs/research_reports/RRA3368-1.html">
    <h3>Understanding China's Naval Maintenance Management</h3>
  </a>
  <span>Research Report</span>
</article>
"""

    articles = parse_core_site_reports(
        html,
        "https://www.rand.org/pubs.html",
        CORE_SITE_CONFIGS["rand"],
    )

    assert [article["title"] for article in articles] == [
        "Understanding China's Naval Maintenance Management",
    ]


def test_parse_cfr_reports_filters_to_report_paths() -> None:
    html = """
<li>
  <a href="/reports/china-strategy-2026">
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
<li>
  <a href="/reports/global-health-strategy">
    <h2>Global Health Strategy</h2>
  </a>
  <span>Report</span>
</li>
"""

    articles = parse_core_site_reports(
        html,
        "https://www.cfr.org/report",
        CORE_SITE_CONFIGS["cfr"],
    )

    assert [article["url"] for article in articles] == [
        "https://www.cfr.org/reports/china-strategy-2026",
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


def test_parse_china_context_page_rejects_generic_listing_links() -> None:
    html = """
<div class="publication-card">
  <a href="/publications/working-papers">
    <h3>Publications</h3>
  </a>
  <span>Working Papers</span>
</div>
<div class="publication-card">
  <a href="/publications/policy-briefs">
    <h3>Policy Briefs</h3>
  </a>
</div>
<div class="publication-card">
  <a href="/publications/working-papers/2026/china-supply-chain-policy">
    <h3>China supply chain policy</h3>
  </a>
  <span>Working Paper</span>
</div>
"""

    articles = parse_core_site_reports(
        html,
        "https://www.piie.com/research/china",
        CORE_SITE_CONFIGS["piie"],
    )

    assert [article["title"] for article in articles] == [
        "China supply chain policy",
    ]


def test_parse_china_context_page_rejects_view_more_listing_links() -> None:
    html = """
<div class="publication-card">
  <a href="/publications/working-papers">View more</a>
</div>
<div class="publication-card">
  <a href="/publications/working-papers/2026/china-supply-chain-policy">
    <h3>China supply chain policy</h3>
  </a>
  <span>Working Paper</span>
</div>
"""

    articles = parse_core_site_reports(
        html,
        "https://www.piie.com/research/china",
        CORE_SITE_CONFIGS["piie"],
    )

    assert [article["title"] for article in articles] == [
        "China supply chain policy",
    ]


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


def test_parse_heritage_reports_keeps_china_report_paths() -> None:
    html = """
<article>
  <a href="/asia/report/china-threat-assessment">
    <h3>China Threat Assessment</h3>
  </a>
  <span>Report</span>
  <span>September 9, 2026</span>
</article>
<article>
  <a href="/asia/commentary/china-news">
    <h3>China news commentary</h3>
  </a>
  <span>Commentary</span>
</article>
"""

    articles = parse_core_site_reports(
        html,
        "https://www.heritage.org/china",
        CORE_SITE_CONFIGS["heritage"],
    )

    assert articles == [
        {
            "title": "China Threat Assessment",
            "url": "https://www.heritage.org/asia/report/china-threat-assessment",
            "published_at": datetime(2026, 9, 9),
            "content_type": "report",
            "allow_web_article_fallback": True,
        }
    ]


def test_link_text_title_takes_priority_over_outer_topic_heading() -> None:
    html = """
<section>
  <h2>China</h2>
  <article>
    <a href="/china/report/china-threat-assessment">
      China Threat Assessment
    </a>
    <span>Report</span>
    <span>September 9, 2026</span>
  </article>
</section>
"""

    articles = parse_core_site_reports(
        html,
        "https://www.heritage.org/china",
        CORE_SITE_CONFIGS["heritage"],
    )

    assert [article["title"] for article in articles] == [
        "China Threat Assessment",
    ]


def test_parse_aei_reports_accepts_aeistats_report_listing() -> None:
    html = """
<div class="card">
  <a href="/research-products/reports/china-tech-competition">
    <h3>China Technology Competition</h3>
  </a>
  <span>Report</span>
  <span>September 10, 2026</span>
</div>
<div class="card">
  <a href="/research-products/reports/education-report">
    <h3>Education report</h3>
  </a>
  <p>China appears elsewhere in the same listing container.</p>
  <span>Report</span>
</div>
<div class="card">
  <a href="/events/china-policy-panel">
    <h3>China policy panel</h3>
  </a>
  <span>Event</span>
</div>
"""

    articles = parse_core_site_reports(
        html,
        "https://aeistats.aei.org/research-products/reports/",
        CORE_SITE_CONFIGS["aei"],
    )

    assert [article["url"] for article in articles] == [
        "https://aeistats.aei.org/research-products/reports/china-tech-competition",
    ]


def test_parse_aei_china_tag_page_still_requires_candidate_china_signal() -> None:
    html = """
<div class="card">
  <a href="/research-products/report/education-report">
    <h3>Education report</h3>
  </a>
  <span>Report</span>
</div>
<div class="card">
  <a href="/research-products/report/china-tech-report">
    <h3>China tech report</h3>
  </a>
  <span>Report</span>
</div>
"""

    articles = parse_core_site_reports(
        html,
        "https://www.aei.org/tag/china/",
        CORE_SITE_CONFIGS["aei"],
    )

    assert [article["title"] for article in articles] == [
        "China tech report",
    ]


def test_parse_hoover_publications_require_china_signal() -> None:
    html = """
<article>
  <a href="/publications/us-policy-report">
    <h3>US policy report</h3>
  </a>
  <span>Report</span>
</article>
<article>
  <a href="/publications/china-sharp-power-report">
    <h3>China sharp power report</h3>
  </a>
  <span>Report</span>
</article>
"""

    articles = parse_core_site_reports(
        html,
        "https://www.hoover.org/publications",
        CORE_SITE_CONFIGS["hoover"],
    )

    assert [article["title"] for article in articles] == [
        "China sharp power report",
    ]


def test_parse_hoover_publications_uses_card_title_for_cta_links() -> None:
    html = """
<article>
  <h3>Autocrats vs. Democrats: China, Russia, America, and Global Disorder</h3>
  <a href="/research/autocrats-vs-democrats-china-russia-america-and-new-global-disorder">
    learn more
  </a>
  <span>Report</span>
</article>
"""

    articles = parse_core_site_reports(
        html,
        "https://www.hoover.org/publications",
        CORE_SITE_CONFIGS["hoover"],
    )

    assert [article["title"] for article in articles] == [
        "Autocrats vs. Democrats: China, Russia, America, and Global Disorder",
    ]


def test_parse_wilson_center_publications_require_china_signal() -> None:
    html = """
<li>
  <a href="/publication/china-supply-chain-resilience">
    <h2>China Supply Chain Resilience</h2>
  </a>
  <span>Report</span>
  <span>10 September 2026</span>
</li>
<li>
  <a href="/publication/supply-chain-resilience">
    <h2>Supply Chain Resilience</h2>
  </a>
  <span>Report</span>
</li>
"""

    articles = parse_core_site_reports(
        html,
        "https://www.wilsoncenter.org/publications",
        CORE_SITE_CONFIGS["wilson"],
    )

    assert articles[0]["title"] == "China Supply Chain Resilience"
    assert articles[0]["url"] == (
        "https://www.wilsoncenter.org/publication/china-supply-chain-resilience"
    )
    assert articles[0]["published_at"] == datetime(2026, 9, 10)


def test_parse_wilson_center_search_keeps_china_article_candidates() -> None:
    html = """
<article class="search-result js-link-event" data-content-type="article">
  <header class="text">
    <div class="tags">
      <ul class="tags-list">
        <li class="tag" data-category="article">Article</li>
      </ul>
    </div>
    <h2 class="title h4 -blue-600">
      <a href="/article/china-strategy-report" class="js-link-event-link">
        China Strategy Report
      </a>
    </h2>
    <time datetime="2026-09-10T12:30:00-04:00">September 10, 2026</time>
  </header>
</article>
<article class="search-result js-link-event" data-content-type="article">
  <h2>
    <a href="/article/global-security-roundup">Global Security Roundup</a>
  </h2>
</article>
"""

    articles = parse_core_site_reports(
        html,
        "https://www.wilsoncenter.org/search?search=China",
        CORE_SITE_CONFIGS["wilson"],
    )

    assert [article["url"] for article in articles] == [
        "https://www.wilsoncenter.org/article/china-strategy-report",
    ]


def test_parse_cato_policy_analysis_requires_china_signal() -> None:
    html = """
<article>
  <a href="/policy-analysis/china-trade-policy-after-2026">
    <h3>China Trade Policy After 2026</h3>
  </a>
  <span>Policy Analysis</span>
  <span>September 11, 2026</span>
</article>
<article>
  <a href="/blog/china-news">
    <h3>China news blog</h3>
  </a>
  <span>Blog</span>
</article>
<article>
  <a href="/policy-analysis/tax-policy-after-2026">
    <h3>Tax Policy After 2026</h3>
  </a>
  <span>Policy Analysis</span>
</article>
"""

    articles = parse_core_site_reports(
        html,
        "https://www.cato.org/policy-analysis",
        CORE_SITE_CONFIGS["cato"],
    )

    assert articles == [
        {
            "title": "China Trade Policy After 2026",
            "url": (
                "https://www.cato.org/policy-analysis/"
                "china-trade-policy-after-2026"
            ),
            "published_at": datetime(2026, 9, 11),
            "content_type": "policy_brief",
            "allow_web_article_fallback": True,
        }
    ]


def test_parse_nber_working_papers_requires_china_signal() -> None:
    html = """
<li>
  <a href="/papers/w34567">
    <h3>China Supply Chains and Global Trade</h3>
  </a>
  <span>Working Paper</span>
  <span>September 12, 2026</span>
</li>
<li>
  <a href="/digest/2026/china-summary">
    <h3>China digest summary</h3>
  </a>
</li>
<li>
  <a href="/papers/w34568">
    <h3>Labor Market Dynamics</h3>
  </a>
  <span>Working Paper</span>
</li>
"""

    articles = parse_core_site_reports(
        html,
        "https://www.nber.org/papers",
        CORE_SITE_CONFIGS["nber"],
    )

    assert articles == [
        {
            "title": "China Supply Chains and Global Trade",
            "url": "https://www.nber.org/papers/w34567",
            "published_at": datetime(2026, 9, 12),
            "content_type": "working_paper",
            "allow_web_article_fallback": False,
        }
    ]
