from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from app.services.crawler.report_candidate_filter import has_china_signal

DATE_PATTERNS = (
    re.compile(r"\b([A-Z][a-z]+ \d{1,2}, \d{4})\b"),
    re.compile(r"\b(\d{1,2} [A-Z][a-z]+ \d{4})\b"),
)


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _is_cap_article_url(url: str) -> bool:
    parsed = urlsplit(url)

    if parsed.netloc.lower() not in {
        "www.americanprogress.org",
        "americanprogress.org",
    }:
        return False

    return parsed.path.startswith("/article/")


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


def _has_report_type_label(value: str) -> bool:
    return re.search(
        r"(?<![A-Za-z])Report(?![A-Za-z])",
        value,
    ) is not None


def parse_cap_reports(
    html: str | bytes,
    base_url: str,
) -> list[dict[str, object]]:
    """
    Parse Center for American Progress listing pages.

    CAP uses /article/ for both ordinary articles and formal reports. The
    parser therefore requires an explicit "Report" label in the nearest card
    text before returning a candidate.
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

        if url in seen_urls or not _is_cap_article_url(url):
            continue

        container = _nearest_text_container(link)
        container_text = _clean_text(
            container.get_text(" ", strip=True)
        )

        if not _has_report_type_label(container_text):
            continue

        title = _title_from_link(
            link,
            container,
        )

        if not title:
            continue

        if not is_china_context_page and not has_china_signal(
            title=title,
            url=url,
            text=container_text,
        ):
            continue

        seen_urls.add(url)
        reports.append(
            {
                "title": title[:500],
                "url": url,
                "published_at": _parse_date_from_text(container_text),
                "content_type": "report",
                "allow_web_article_fallback": True,
            }
        )

    return reports
