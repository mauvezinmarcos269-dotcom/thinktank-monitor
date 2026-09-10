import re
from datetime import datetime
from html.entities import html5
from typing import Any
from urllib.parse import urljoin

import feedparser
from bs4 import BeautifulSoup

XML_DEFINED_ENTITIES = {"amp", "lt", "gt", "quot", "apos"}
NAMED_ENTITY_RE = re.compile(r"&([A-Za-z][A-Za-z0-9]+);")
BARE_AMPERSAND_RE = re.compile(
    r"&(?!(?:#\d+|#x[0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]+);)"
)
INVALID_XML_CHAR_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def _to_plain_text(value: object) -> str:
    """去除 RSS 标题或摘要中可能存在的 HTML 标签。"""
    text = BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)
    return " ".join(text.split())


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


def _decode_feed_content(feed_content: bytes) -> str:
    """Decode RSS bytes for fallback cleanup when XML parsing rejects entities."""
    encoding_match = re.search(
        rb"<\?xml[^>]+encoding=[\"']([^\"']+)[\"']",
        feed_content[:200],
        flags=re.IGNORECASE,
    )
    encodings = [encoding_match.group(1).decode("ascii", errors="ignore")] if encoding_match else []
    encodings.append("utf-8-sig")

    for encoding in encodings:
        if not encoding:
            continue
        try:
            return feed_content.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue

    return feed_content.decode("utf-8-sig", errors="replace")


def _replace_undefined_xml_entities(feed_text: str) -> str:
    """
    Replace HTML named entities that are invalid in XML feeds.

    Some RSS feeds contain entities such as &mdash; or &nbsp; without a DTD. XML
    parsers reject those names, while feedparser can handle the feed after they
    are converted to Unicode characters.
    """

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in XML_DEFINED_ENTITIES:
            return match.group(0)

        replacement = html5.get(f"{name};")
        if replacement is not None:
            return replacement

        return f"&amp;{name};"

    return NAMED_ENTITY_RE.sub(replace, feed_text)


def _clean_feed_text_for_xml(feed_text: str) -> str:
    """
    Normalize common RSS/XML defects before retrying feedparser.

    Real-world feeds occasionally contain HTML-only named entities, bare
    ampersands in links, or invisible control characters. Those are invalid XML
    but safe to repair before parsing.
    """
    cleaned = INVALID_XML_CHAR_RE.sub("", feed_text)
    cleaned = _replace_undefined_xml_entities(cleaned)
    return BARE_AMPERSAND_RE.sub("&amp;", cleaned)


def _parse_feed_with_entity_fallback(feed_content: bytes) -> Any:
    feed_start = feed_content.lstrip()[:500].lower()
    if feed_start.startswith(b"<!doctype html") or feed_start.startswith(b"<html"):
        raise ValueError("RSS 解析失败: 来源返回 HTML 页面，可能 RSS 地址已跳转或失效。")

    feed = feedparser.parse(feed_content)

    if not feed.bozo and feed.entries:
        return feed

    feed_text = _decode_feed_content(feed_content)
    cleaned_feed = _clean_feed_text_for_xml(feed_text)
    if cleaned_feed == feed_text:
        return feed

    retry_feed = feedparser.parse(cleaned_feed)
    if retry_feed.entries and (
        not retry_feed.bozo
        or len(retry_feed.entries) >= len(feed.entries)
    ):
        return retry_feed

    return feed


def parse_rss_articles(feed_content: bytes, base_url: str) -> list[dict[str, object]]:
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
    # feedparser 接收 bytes 是极佳选择，它会读取 XML 声明中的 encoding 属性
    feed = _parse_feed_with_entity_fallback(feed_content)

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
