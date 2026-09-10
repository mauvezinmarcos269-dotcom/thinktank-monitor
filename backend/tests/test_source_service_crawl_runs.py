from datetime import datetime, timedelta
from types import SimpleNamespace

from app.services.source_service import SourceService


def test_to_crawl_run_read_calculates_duration_and_defaults_counts() -> None:
    started_at = datetime(2026, 9, 9, 12, 0, 0)
    finished_at = started_at + timedelta(seconds=95)
    crawl_run = SimpleNamespace(
        id=1,
        source_id=5,
        status="success",
        found_count=None,
        saved_count=None,
        error=None,
        started_at=started_at,
        finished_at=finished_at,
        created_at=started_at,
    )

    result = SourceService()._to_crawl_run_read(crawl_run)

    assert result.duration_seconds == 95
    assert result.found_count == 0
    assert result.saved_count == 0
