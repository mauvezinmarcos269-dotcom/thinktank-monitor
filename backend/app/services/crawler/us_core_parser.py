from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from app.services.crawler.report_candidate_filter import (
    has_china_signal,
    is_heavy_report_candidate,
)

DATE_PATTERNS = (
    re.compile(r"\b([A-Z][a-z]+ \d{1,2}, \d{4})\b"),
    re.compile(r"\b(\d{1,2} [A-Z][a-z]+ \d{4})\b"),
)

GENERIC_LISTING_TITLES = {
    "articles",
    "briefings",
    "learn more",
    "papers",
    "piie briefings",
    "policy briefs",
    "publication",
    "publications",
    "read more",
    "report",
    "reports",
    "research",
    "view more",
    "working paper",
    "working papers",
}

GENERIC_LINK_TEXTS = {
    "learn more",
    "read more",
    "view more",
}


@dataclass(frozen=True)
class CoreSiteConfig:
    name: str
    hosts: frozenset[str]
    discovery_urls: tuple[str, ...]
    path_prefixes: tuple[str, ...]
    require_china_signal: bool = False
    require_china_signal_in_title_or_url: bool = False
    content_type: str = "report"
    allow_web_article_fallback: bool = False


CORE_SITE_CONFIGS: dict[str, CoreSiteConfig] = {
    "rand": CoreSiteConfig(
        name="RAND",
        hosts=frozenset({"www.rand.org", "rand.org"}),
        discovery_urls=(
            "https://www.rand.org/pubs.html",
            "https://www.rand.org/pubs/research_reports.html",
            "https://www.rand.org/topics/china.html",
        ),
        path_prefixes=(
            "/pubs/",
        ),
        require_china_signal=True,
        require_china_signal_in_title_or_url=True,
        content_type="research_report",
    ),
    "carnegie": CoreSiteConfig(
        name="Carnegie Endowment",
        hosts=frozenset({"carnegieendowment.org", "www.carnegieendowment.org"}),
        discovery_urls=(
            "https://carnegieendowment.org/research?lang=en",
            "https://carnegieendowment.org/research/regions/china?lang=en",
        ),
        path_prefixes=(
            "/research/",
            "/posts/",
            "/publications/",
        ),
        require_china_signal=True,
        content_type="research",
        allow_web_article_fallback=True,
    ),
    "cfr": CoreSiteConfig(
        name="Council on Foreign Relations",
        hosts=frozenset({"www.cfr.org", "cfr.org"}),
        discovery_urls=(
            "https://www.cfr.org/reports",
            "https://www.cfr.org/regions/asia/china",
        ),
        path_prefixes=(
            "/report/",
            "/reports/",
            "/paper/",
        ),
        require_china_signal=True,
        content_type="report",
    ),
    "piie": CoreSiteConfig(
        name="Peterson Institute for International Economics",
        hosts=frozenset({"www.piie.com", "piie.com"}),
        discovery_urls=(
            "https://www.piie.com/research/publications",
            "https://www.piie.com/research/china",
        ),
        path_prefixes=(
            "/research/publications/",
            "/publications/",
        ),
        require_china_signal=True,
        content_type="publication",
        allow_web_article_fallback=True,
    ),
    "heritage": CoreSiteConfig(
        name="The Heritage Foundation",
        hosts=frozenset({"www.heritage.org", "heritage.org"}),
        discovery_urls=(
            "https://www.heritage.org/asia",
            "https://www.heritage.org/china",
            "https://www.heritage.org/china?f%5B0%5D=content_type%3Areport",
        ),
        path_prefixes=(
            "/asia/report/",
            "/china/report/",
            "/china-plan",
            "/defense/report/",
            "/global-politics/report/",
            "/trade/report/",
        ),
        require_china_signal=True,
        require_china_signal_in_title_or_url=True,
        content_type="report",
        allow_web_article_fallback=True,
    ),
    "aei": CoreSiteConfig(
        name="American Enterprise Institute",
        hosts=frozenset({"www.aei.org", "aei.org", "aeistats.aei.org"}),
        discovery_urls=(
            "https://www.aei.org/research-products/report/",
            "https://aeistats.aei.org/research-products/reports/",
            "https://www.aei.org/tag/china/",
        ),
        path_prefixes=(
            "/research-products/report/",
            "/research-products/reports/",
        ),
        require_china_signal=True,
        require_china_signal_in_title_or_url=True,
        content_type="report",
        allow_web_article_fallback=True,
    ),
    "hoover": CoreSiteConfig(
        name="Hoover Institution",
        hosts=frozenset({"www.hoover.org", "hoover.org"}),
        discovery_urls=(
            "https://www.hoover.org/research/topic/china",
            "https://www.hoover.org/publications",
        ),
        path_prefixes=(
            "/research/",
            "/publications/",
        ),
        require_china_signal=True,
        require_china_signal_in_title_or_url=True,
        content_type="publication",
        allow_web_article_fallback=True,
    ),
    "wilson": CoreSiteConfig(
        name="Wilson Center",
        hosts=frozenset({"www.wilsoncenter.org", "wilsoncenter.org"}),
        discovery_urls=(
            "https://www.wilsoncenter.org/search?search=China",
            "https://www.wilsoncenter.org/insight-analysis",
            "https://www.wilsoncenter.org/publications",
        ),
        path_prefixes=(
            "/article/",
            "/publication/",
            "/report/",
        ),
        require_china_signal=True,
        require_china_signal_in_title_or_url=True,
        content_type="report",
        allow_web_article_fallback=True,
    ),
    "cato": CoreSiteConfig(
        name="Cato Institute",
        hosts=frozenset({"www.cato.org", "cato.org"}),
        discovery_urls=(
            "https://www.cato.org/policy-analysis",
            "https://www.cato.org/search/category/policy-analysis?query=China",
        ),
        path_prefixes=(
            "/policy-analysis/",
        ),
        require_china_signal=True,
        require_china_signal_in_title_or_url=True,
        content_type="policy_brief",
        allow_web_article_fallback=True,
    ),
    "nber": CoreSiteConfig(
        name="National Bureau of Economic Research",
        hosts=frozenset({"www.nber.org", "nber.org"}),
        discovery_urls=(
            "https://www.nber.org/papers",
            "https://www.nber.org/search?search=China",
        ),
        path_prefixes=(
            "/papers/",
        ),
        require_china_signal=True,
        require_china_signal_in_title_or_url=True,
        content_type="working_paper",
    ),
}


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _parse_date_from_text(value: str) -> datetime | None:
    for pattern in DATE_PATTERNS:
        match = pattern.search(value)
        if match is None:
            continue

        raw_value = match.group(1)
        for date_format in (
            "%B %d, %Y",
            "%d %B %Y",
        ):
            try:
                return datetime.strptime(
                    raw_value,
                    date_format,
                )
            except ValueError:
                continue

    return None


def _is_supported_url(
    url: str,
    config: CoreSiteConfig,
) -> bool:
    parsed = urlsplit(url)
    if parsed.netloc.lower() not in config.hosts:
        return False

    return parsed.path.startswith(config.path_prefixes)


def _is_generic_listing_link(
    *,
    title: str,
    url: str,
) -> bool:
    normalized_title = _clean_text(title).lower()

    if normalized_title not in GENERIC_LISTING_TITLES:
        return False

    path_parts = [
        part
        for part in urlsplit(url).path.strip("/").split("/")
        if part
    ]
    return len(path_parts) <= 2


def _nearest_text_container(link: Tag) -> Tag:
    return (
        link.find_parent("article")
        or link.find_parent("li")
        or link.find_parent("div")
        or link
    )


def _title_from_link(
    link: Tag,
    container: Tag,
) -> str:
    for selector in (
        "h1",
        "h2",
        "h3",
        "h4",
        ".title",
        ".card-title",
        ".publication-title",
    ):
        node = link.select_one(selector)
        if node is not None:
            title = _clean_text(node.get_text(" ", strip=True))
            if title:
                return title

    link_text = _clean_text(link.get_text(" ", strip=True))
    if link_text and link_text.lower() not in GENERIC_LINK_TEXTS:
        return link_text

    for attribute in (
        "aria-label",
        "title",
    ):
        value = link.get(attribute)
        if value:
            title = _clean_text(str(value))
            if title:
                return title

    for selector in (
        "h1",
        "h2",
        "h3",
        "h4",
        ".title",
        ".card-title",
        ".publication-title",
    ):
        node = container.select_one(selector)
        if node is not None:
            title = _clean_text(node.get_text(" ", strip=True))
            if title:
                return title

    return ""


def parse_core_site_reports(
    html: str | bytes,
    base_url: str,
    config: CoreSiteConfig,
) -> list[dict[str, object]]:
    """
    Parse report/publication listing pages for core US think tanks.

    The parser intentionally uses broad semantic HTML patterns because these
    sites regularly change class names. Site-specific URL prefixes and the
    heavy-report pre-filter keep the output conservative.
    """
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    reports: list[dict[str, object]] = []
    seen_urls: set[str] = set()
    is_china_context_page = has_china_signal(
        title="",
        url=base_url,
    )

    for link in soup.select("a[href]"):
        href = str(link.get("href", "")).strip()
        if not href or href.startswith(("#", "mailto:", "tel:")):
            continue

        url = urljoin(
            base_url,
            href,
        )

        if url in seen_urls or not _is_supported_url(
            url,
            config,
        ):
            continue

        container = _nearest_text_container(link)
        title = _title_from_link(
            link,
            container,
        )
        container_text = _clean_text(
            container.get_text(" ", strip=True)
        )

        if not is_heavy_report_candidate(
            title=title,
            url=url,
            text=(
                ""
                if config.require_china_signal_in_title_or_url
                else container_text
            ),
            content_type=config.content_type,
            require_china_signal=(
                config.require_china_signal
                and (
                    config.require_china_signal_in_title_or_url
                    or not is_china_context_page
                )
            ),
        ):
            continue

        if _is_generic_listing_link(
            title=title,
            url=url,
        ):
            continue

        seen_urls.add(url)
        reports.append(
            {
                "title": title[:500],
                "url": url,
                "published_at": _parse_date_from_text(container_text),
                "content_type": config.content_type,
                "allow_web_article_fallback": config.allow_web_article_fallback,
            }
        )

    return reports
