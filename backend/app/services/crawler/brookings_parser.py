from __future__ import annotations

from datetime import datetime
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

BROOKINGS_CONTENT_PATH_PREFIXES = (
    "/articles/",
    "/essay/",
    "/reports/",
    "/research/",
)
BROOKINGS_REPORT_PATH_PREFIXES = (
    "/essay/",
    "/reports/",
    "/research/",
)
BROOKINGS_CHINA_CONTEXT_PATH_PREFIXES = (
    "/regions/asia-the-pacific/china/",
)
BROOKINGS_CHINA_TERMS = (
    "beijing",
    "china",
    "chinese",
    "hong kong",
    "prc",
    "sino",
    "taiwan",
    "u.s.-china",
    "us-china",
    "xi jinping",
)


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _parse_brookings_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(
            value.strip(),
            "%B %d, %Y",
        )
    except ValueError:
        return None


def _is_brookings_content_url(url: str) -> bool:
    parsed = urlsplit(url)

    if parsed.netloc.lower() not in {
        "www.brookings.edu",
        "brookings.edu",
    }:
        return False

    return parsed.path.startswith(BROOKINGS_CONTENT_PATH_PREFIXES)


def _is_brookings_report_style_url(url: str) -> bool:
    return urlsplit(url).path.startswith(BROOKINGS_REPORT_PATH_PREFIXES)


def _is_brookings_web_article_url(url: str) -> bool:
    return urlsplit(url).path.startswith("/articles/")


def _is_brookings_china_context_page(base_url: str) -> bool:
    return urlsplit(base_url).path.startswith(BROOKINGS_CHINA_CONTEXT_PATH_PREFIXES)


def _looks_china_related(title: str, url: str, article_text: str) -> bool:
    haystack = f"{title} {url} {article_text}".lower()
    return any(term in haystack for term in BROOKINGS_CHINA_TERMS)


def parse_brookings_reports(
    html: str | bytes,
    base_url: str,
) -> list[dict[str, object]]:
    """
    Parse Brookings listing pages.

    Brookings no longer returns a usable RSS feed from /feed/ in local testing.
    Its listing pages expose research items as <article> cards, with titles in
    .article-title or the overlay link's screen-reader label.
    """
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    reports: list[dict[str, object]] = []
    seen_urls: set[str] = set()
    is_china_context_page = _is_brookings_china_context_page(base_url)

    for article in soup.select("article"):
        link = article.select_one("a.overlay-link[href]") or article.select_one(
            "a[href]"
        )

        if link is None:
            continue

        href = str(link.get("href", "")).strip()
        url = urljoin(
            base_url,
            href,
        )

        if not _is_brookings_content_url(url) or url in seen_urls:
            continue

        title_node = article.select_one(".article-title")
        title = (
            _clean_text(title_node.get_text(" ", strip=True))
            if title_node is not None
            else _clean_text(link.get_text(" ", strip=True))
        )

        if not title:
            sr_only = link.select_one(".sr-only")
            title = (
                _clean_text(sr_only.get_text(" ", strip=True))
                if sr_only is not None
                else ""
            )

        if not title:
            continue

        article_text = _clean_text(
            article.get_text(" ", strip=True)
        )

        if (
            not _is_brookings_report_style_url(url)
            and not is_china_context_page
            and not _looks_china_related(title, url, article_text)
        ):
            continue

        date_node = article.select_one(".date")
        published_at = (
            _parse_brookings_date(date_node.get_text(" ", strip=True))
            if date_node is not None
            else None
        )

        seen_urls.add(url)
        reports.append(
            {
                "title": title[:500],
                "url": url,
                "published_at": published_at,
                "content_type": (
                    "web_article"
                    if _is_brookings_web_article_url(url)
                    else "report"
                ),
                "allow_web_article_fallback": (
                    _is_brookings_web_article_url(url)
                ),
            }
        )

    return reports
