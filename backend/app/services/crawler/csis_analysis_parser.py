from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

DATE_PATTERN = re.compile(
    r"(?:—|-)\s*([A-Za-z]+ \d{1,2}, \d{4})"
)
REPORT_BY_PATTERN = re.compile(
    r"\bReport\s*(?:by\b|[—-])",
    re.IGNORECASE,
)


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _parse_date(value: str) -> datetime | None:
    date_match = DATE_PATTERN.search(
        value
    )

    if date_match is None:
        return None

    try:
        return datetime.strptime(
            date_match.group(1),
            "%B %d, %Y",
        )
    except ValueError:
        return None


def _parse_datetime_attribute(node: Tag) -> datetime | None:
    time_node = node.select_one(
        "time[datetime]"
    )

    if time_node is None:
        return None

    value = str(
        time_node.get(
            "datetime",
            "",
        )
    ).strip()

    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        ).replace(tzinfo=None)
    except ValueError:
        return None


def _is_report_result(node: Tag) -> bool:
    text = _clean_text(
        node.get_text(
            " ",
            strip=True,
        )
    )

    if REPORT_BY_PATTERN.search(text):
        return True

    for selector in (
        ".content-type",
        ".type",
        ".tag",
        ".label",
    ):
        for type_node in node.select(selector):
            if _clean_text(type_node.get_text(" ", strip=True)).lower() == "report":
                return True

    return False


def _extract_title_link(node: Tag) -> Tag | None:
    for selector in (
        "h3 a[href]",
        "h2 a[href]",
        "h4 a[href]",
        ".title a[href]",
        "a[href]",
    ):
        link = node.select_one(selector)
        if link is not None:
            return link

    return None


def _append_report_from_node(
    *,
    node: Tag,
    base_url: str,
    reports: list[dict[str, object]],
    seen_urls: set[str],
) -> None:
    title_link = _extract_title_link(node)

    if title_link is None:
        return

    title = _clean_text(
        title_link.get_text(
            " ",
            strip=True,
        )
    )
    href = str(
        title_link.get(
            "href",
            "",
        )
    ).strip()

    if not title or not href:
        return

    url = urljoin(
        base_url,
        href,
    )

    if url in seen_urls:
        return

    seen_urls.add(url)
    article_text = _clean_text(
        node.get_text(
            " ",
            strip=True,
        )
    )
    published_at = _parse_datetime_attribute(
        node
    ) or _parse_date(
        article_text
    )

    reports.append(
        {
            "title": title,
            "url": url,
            "published_at": published_at,
            "content_type": "report",
        }
    )


def parse_csis_reports(
    html: str | bytes,
    base_url: str,
) -> list[dict[str, object]]:
    """
    解析 CSIS /analysis 列表页。

    这里只提取正式 Report 类型，
    Commentary、Critical Questions、活动等不会返回。
    """
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    reports: list[dict[str, object]] = []
    seen_urls: set[str] = set()

    for article in soup.select(
        "article.report-search-listing"
    ):
        if not _is_report_result(article):
            continue

        _append_report_from_node(
            node=article,
            base_url=base_url,
            reports=reports,
            seen_urls=seen_urls,
        )

    for article in soup.select(
        ".search-result, .views-row"
    ):
        if not _is_report_result(article):
            continue

        _append_report_from_node(
            node=article,
            base_url=base_url,
            reports=reports,
            seen_urls=seen_urls,
        )

    return reports
