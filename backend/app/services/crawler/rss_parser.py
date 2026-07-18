from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import feedparser
from bs4 import BeautifulSoup


def _to_plain_text(value: object) -> str:
    """去除 RSS 标题或摘要中可能存在的 HTML 标签。"""
    return BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)


def _parse_published_at(entry: Any) -> datetime | None:
    """RSS 时间统一解析为 UTC 的无时区 datetime，与当前 reports 表保持一致。"""
    parsed_time = (
        entry.get("published_parsed")
        or entry.get("updated_parsed")
        or entry.get("created_parsed")
    )

    if not parsed_time:
        return None

    return datetime(
        parsed_time.tm_year,
        parsed_time.tm_mon,
        parsed_time.tm_mday,
        parsed_time.tm_hour,
        parsed_time.tm_min,
        parsed_time.tm_sec,
    )


def parse_rss_articles(feed_content: str, base_url: str) -> list[dict[str, object]]:
    """
    解析 RSS 或 Atom 内容。

    返回格式：
    [
        {
            "title": "...",
            "url": "https://...",
            "content": "...",
            "published_at": datetime | None,
        }
    ]
    """
    feed = feedparser.parse(feed_content)

    if feed.bozo and not feed.entries:
        error = getattr(feed, "bozo_exception", None)
        raise ValueError(f"RSS 解析失败: {error or '未发现有效条目'}")

    articles: list[dict[str, object]] = []

    for entry in feed.entries:
        title = _to_plain_text(entry.get("title", ""))
        link = str(entry.get("link", "")).strip()

        if not title or not link:
            continue

        content_raw = (
            entry.get("summary")
            or entry.get("description")
            or entry.get("content", "")
        )

        if isinstance(content_raw, list):
            content_raw = content_raw[0].get("value", "") if content_raw else ""

        content = _to_plain_text(content_raw) if content_raw else None

        articles.append(
            {
                "title": title[:500],
                "url": urljoin(base_url, link),
                "content": content,
                "published_at": _parse_published_at(entry),
            }
        )

    return articles
