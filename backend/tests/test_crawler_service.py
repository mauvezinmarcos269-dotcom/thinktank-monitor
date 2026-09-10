from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.services.crawler_service import _is_source_due_for_crawl


def make_source(
    *,
    last_crawled_at,
    crawl_frequency_minutes: int = 1440,
):
    return SimpleNamespace(
        last_crawled_at=last_crawled_at,
        crawl_frequency_minutes=crawl_frequency_minutes,
    )


def test_source_without_last_crawl_is_due() -> None:
    now = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)

    assert _is_source_due_for_crawl(
        make_source(last_crawled_at=None),
        now=now,
    )


def test_source_is_not_due_before_frequency_window() -> None:
    now = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)

    assert not _is_source_due_for_crawl(
        make_source(
            last_crawled_at=now - timedelta(minutes=30),
            crawl_frequency_minutes=60,
        ),
        now=now,
    )


def test_source_is_due_after_frequency_window() -> None:
    now = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)

    assert _is_source_due_for_crawl(
        make_source(
            last_crawled_at=now - timedelta(minutes=61),
            crawl_frequency_minutes=60,
        ),
        now=now,
    )


def test_source_due_check_accepts_naive_database_time() -> None:
    now = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
    naive_last_crawled_at = datetime(2026, 9, 7, 10, 59)

    assert _is_source_due_for_crawl(
        make_source(
            last_crawled_at=naive_last_crawled_at,
            crawl_frequency_minutes=60,
        ),
        now=now,
    )
