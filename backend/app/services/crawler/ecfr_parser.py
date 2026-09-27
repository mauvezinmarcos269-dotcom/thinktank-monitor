from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from app.services.crawler.report_candidate_filter import has_china_signal

ECFR_HOSTS = {
    "ecfr.eu",
    "www.ecfr.eu",
}

REPORT_LABELS = (
    "policy brief",
    "policy alert",
    "special",
    "book",
    "report",
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


def _is_ecfr_publication_url(url: str) -> bool:
    parsed = urlsplit(url)

    if parsed.netloc.lower() not in ECFR_HOSTS:
        return False

    return parsed.path.startswith("/publication/")


def _content_label(card_text: str) -> str:
    lowered = card_text.lower()

    for label in REPORT_LABELS:
        if re.search(
            rf"(?<![a-z]){re.escape(label)}(?![a-z])",
            lowered,
        ):
            return label

    return ""


def _title_from_card(
    card: Tag,
    link: Tag,
    label: str,
) -> str:
    for selector in (
        "h1",
        "h2",
        "h3",
        "h4",
    ):
        node = card.select_one(selector)
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


def _is_china_context_page(base_url: str) -> bool:
    path = urlsplit(base_url).path.lower()
    return path.startswith(("/topic/china", "/category/china"))


def parse_ecfr_reports(
    html: str | bytes,
    base_url: str,
) -> list[dict[str, object]]:
    """Parse ECFR listing pages for report-style publication cards."""
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    reports: list[dict[str, object]] = []
    seen_urls: set[str] = set()
    is_china_context_page = _is_china_context_page(base_url)

    for card in soup.select("article"):
        link = card.select_one("a[href*='/publication/']")
        if link is None:
            continue

        url = urljoin(
            base_url,
            str(link.get("href", "")).strip(),
        )

        if url in seen_urls or not _is_ecfr_publication_url(url):
            continue

        card_text = _clean_text(
            card.get_text(
                " ",
                strip=True,
            )
        )
        label = _content_label(card_text)

        if label not in REPORT_LABEL_SET:
            continue

        title = _title_from_card(
            card,
            link,
            label,
        )

        if not title:
            continue

        if (
            not is_china_context_page
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
                "content_type": label.replace(" ", "_"),
                "allow_web_article_fallback": True,
            }
        )

    return reports
