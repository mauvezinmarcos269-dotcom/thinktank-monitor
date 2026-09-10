from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

DATE_PATTERN = re.compile(
    r"—\s*([A-Za-z]+ \d{1,2}, \d{4})"
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
        title_link = article.select_one(
            "h3 a[href]"
        )

        if title_link is None:
            continue

        title = " ".join(
            title_link.stripped_strings
        ).strip()

        href = title_link.get(
            "href",
            "",
        ).strip()

        if not title or not href:
            continue

        url = urljoin(
            base_url,
            href,
        )

        if url in seen_urls:
            continue

        seen_urls.add(url)

        article_text = " ".join(
            article.stripped_strings
        ).strip()

        published_at = None

        date_match = DATE_PATTERN.search(
            article_text
        )

        if date_match:
            try:
                published_at = datetime.strptime(
                    date_match.group(1),
                    "%B %d, %Y",
                )
            except ValueError:
                published_at = None

        reports.append(
            {
                "title": title,
                "url": url,
                "published_at": published_at,
                "content_type": "report",
            }
        )

    return reports
