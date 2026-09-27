from __future__ import annotations

import json
from datetime import datetime
from urllib.parse import urljoin

from app.services.crawler.report_candidate_filter import has_china_signal


def _parse_display_date(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None

    for date_format in (
        "%B %d, %Y",
        "%B %Y",
        "%Y",
    ):
        try:
            return datetime.strptime(
                value,
                date_format,
            )
        except ValueError:
            continue

    return None


def parse_nber_working_papers(
    content: str | bytes,
    base_url: str,
) -> list[dict[str, object]]:
    data = json.loads(content)
    results = data.get(
        "results",
        [],
    )

    papers: list[dict[str, object]] = []
    seen_urls: set[str] = set()

    for item in results:
        if not isinstance(item, dict) or item.get("type") != "working_paper":
            continue

        title = str(
            item.get("title") or ""
        ).strip()
        raw_url = str(
            item.get("url") or ""
        ).strip()

        if not title or not raw_url:
            continue

        url = urljoin(
            base_url,
            raw_url,
        )

        if url in seen_urls or "/papers/" not in url:
            continue

        if not has_china_signal(
            title=title,
            url=url,
        ):
            continue

        seen_urls.add(url)
        papers.append(
            {
                "title": title[:500],
                "url": url,
                "published_at": _parse_display_date(
                    item.get("displaydate")
                ),
                "content_type": "working_paper",
            }
        )

    return papers
