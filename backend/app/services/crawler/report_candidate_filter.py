from __future__ import annotations

import re
from urllib.parse import urlsplit

REPORT_STYLE_CONTENT_TYPES = {
    "briefing",
    "paper",
    "policy_brief",
    "publication",
    "report",
    "research",
    "research_report",
    "working_paper",
}

REPORT_URL_TERMS = (
    "/analysis/",
    "/paper",
    "/papers/",
    "/perspective",
    "/perspectives/",
    "/publication",
    "/publications/",
    "/pubs/",
    "/report",
    "/reports/",
    "/research/",
    "/working-paper",
    "/working-papers/",
)

REPORT_TITLE_TERMS = (
    "assessment",
    "brief",
    "paper",
    "policy brief",
    "report",
    "research",
    "study",
    "working paper",
)

LIGHTWEIGHT_URL_TERMS = (
    "/audio/",
    "/blog/",
    "/commentary/",
    "/events/",
    "/expert/",
    "/experts/",
    "/interview",
    "/multimedia/",
    "/news/",
    "/opinion/",
    "/podcast",
    "/press/",
    "/transcript",
    "/video/",
    "/webinar",
)

LIGHTWEIGHT_TITLE_TERMS = (
    "blog",
    "commentary",
    "event",
    "interview",
    "podcast",
    "press release",
    "transcript",
    "video",
    "webinar",
)

CHINA_TERMS = (
    "beijing",
    "belt and road",
    "ccp",
    "china",
    "chinese",
    "hong kong",
    "indo-pacific",
    "pla",
    "prc",
    "sino",
    "taiwan",
    "u.s.-china",
    "us-china",
    "xi jinping",
    "xinjiang",
)


def _contains_term(value: str, term: str) -> bool:
    if term.replace("-", "").replace(".", "").replace(" ", "").isalnum():
        return (
            re.search(
                rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])",
                value,
            )
            is not None
        )

    return term in value


def _contains_any(value: str, terms: tuple[str, ...]) -> bool:
    return any(
        _contains_term(
            value,
            term,
        )
        for term in terms
    )


def has_china_signal(
    *,
    title: str,
    url: str,
    text: str = "",
) -> bool:
    haystack = f"{title} {url} {text}".lower()
    return _contains_any(haystack, CHINA_TERMS)


def is_likely_lightweight_candidate(
    *,
    title: str,
    url: str,
    text: str = "",
) -> bool:
    parsed_path = urlsplit(url).path.lower()
    title_text = title.lower()
    haystack = f"{title_text} {text.lower()}"

    return _contains_any(parsed_path, LIGHTWEIGHT_URL_TERMS) or _contains_any(
        haystack,
        LIGHTWEIGHT_TITLE_TERMS,
    )


def is_report_style_candidate(
    *,
    title: str,
    url: str,
    text: str = "",
    content_type: str | None = None,
) -> bool:
    normalized_content_type = (content_type or "").lower().replace(" ", "_")

    if normalized_content_type in REPORT_STYLE_CONTENT_TYPES:
        return True

    parsed_path = urlsplit(url).path.lower()
    haystack = f"{title.lower()} {text.lower()}"

    return _contains_any(parsed_path, REPORT_URL_TERMS) or _contains_any(
        haystack,
        REPORT_TITLE_TERMS,
    )


def is_heavy_report_candidate(
    *,
    title: str,
    url: str,
    text: str = "",
    content_type: str | None = None,
    require_china_signal: bool = False,
) -> bool:
    """
    Conservative pre-filter before downloading documents.

    The final hard gate remains PDF/page extraction and the 20-page threshold.
    This pre-filter only removes obviously lightweight pages and keeps report-
    style candidates for expensive document fetching.
    """
    if not title.strip() or not url.strip():
        return False

    if is_likely_lightweight_candidate(
        title=title,
        url=url,
        text=text,
    ):
        return False

    if require_china_signal and not has_china_signal(
        title=title,
        url=url,
        text=text,
    ):
        return False

    return is_report_style_candidate(
        title=title,
        url=url,
        text=text,
        content_type=content_type,
    )
