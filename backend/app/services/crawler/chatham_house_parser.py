from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from app.services.crawler.report_candidate_filter import has_china_signal

CHATHAM_HOSTS = {
    "www.chathamhouse.org",
    "chathamhouse.org",
}

REPORT_LABELS = (
    "research paper",
    "research report",
    "policy paper",
    "policy brief",
    "briefing",
    "report",
    "paper",
)
REPORT_LABEL_SET = set(REPORT_LABELS)

DATE_PATTERNS = (
    re.compile(r"\b(\d{1,2} [A-Z][a-z]+ \d{4})\b"),
    re.compile(r"\b([A-Z][a-z]+ \d{1,2}, \d{4})\b"),
)


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _parse_date_from_text(value: str) -> datetime | None:
    for pattern in DATE_PATTERNS:
        match = pattern.search(value)
        if match is None:
            continue

        raw_value = match.group(1)
        for date_format in (
            "%d %B %Y",
            "%B %d, %Y",
        ):
            try:
                return datetime.strptime(
                    raw_value,
                    date_format,
                )
            except ValueError:
                continue

    return None


def _is_chatham_url(url: str) -> bool:
    return urlsplit(url).netloc.lower() in CHATHAM_HOSTS


def _content_label(card_text: str) -> str:
    lowered = card_text.lower()

    for label in REPORT_LABELS:
        if re.search(
            rf"(?<![a-z]){re.escape(label)}(?![a-z])",
            lowered,
        ):
            return label

    return ""


def _title_from_article(
    article: Tag,
    link: Tag,
    label: str,
) -> str:
    for selector in (
        "h2",
        "h3",
        "h4",
    ):
        node = article.select_one(selector)
        if node is None:
            continue

        title = _clean_text(
            node.get_text(
                " ",
                strip=True,
            )
        )
        if title:
            return title

    title = _clean_text(
        link.get_text(
            " ",
            strip=True,
        )
    )

    if label and title.lower().startswith(label):
        return _clean_text(title[len(label):])

    return title


def parse_chatham_house_reports(
    html: str | bytes,
    base_url: str,
) -> list[dict[str, object]]:
    """
    Parse Chatham House listing pages.

    The public home page exposes content cards as <article> elements. Some
    deeper listing pages are 403 in the current runtime, so this parser is
    intentionally conservative and works from cards already visible in the
    fetched page.
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

    for article in soup.select("article"):
        link = article.select_one("a[href]")
        if link is None:
            continue

        url = urljoin(
            base_url,
            str(link.get("href", "")).strip(),
        )

        if url in seen_urls or not _is_chatham_url(url):
            continue

        card_text = _clean_text(
            article.get_text(
                " ",
                strip=True,
            )
        )
        label = _content_label(card_text)

        if not label:
            continue

        title = _title_from_article(
            article,
            link,
            label,
        )

        if not title:
            continue

        is_report = label in REPORT_LABEL_SET
        if (
            is_report
            and not is_china_context_page
            and not has_china_signal(
                title=title,
                url=url,
                text=card_text,
            )
        ):
            continue

        seen_urls.add(url)
        reports.append(
            {
                "title": title[:500],
                "url": url,
                "published_at": _parse_date_from_text(card_text),
                "content_type": "research_report",
                "allow_web_article_fallback": True,
            }
        )

    return reports
