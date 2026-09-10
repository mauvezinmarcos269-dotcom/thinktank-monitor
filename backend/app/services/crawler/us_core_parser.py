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


@dataclass(frozen=True)
class CoreSiteConfig:
    name: str
    hosts: frozenset[str]
    discovery_urls: tuple[str, ...]
    path_prefixes: tuple[str, ...]
    require_china_signal: bool = False
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
            "https://www.cfr.org/report",
            "https://www.cfr.org/asia/china",
        ),
        path_prefixes=(
            "/report/",
            "/paper/",
        ),
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
        node = container.select_one(selector)
        if node is not None:
            title = _clean_text(node.get_text(" ", strip=True))
            if title:
                return title

    for attribute in (
        "aria-label",
        "title",
    ):
        value = link.get(attribute)
        if value:
            title = _clean_text(str(value))
            if title:
                return title

    return _clean_text(link.get_text(" ", strip=True))


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
            text=container_text,
            content_type=config.content_type,
            require_china_signal=(
                config.require_china_signal
                and not is_china_context_page
            ),
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
