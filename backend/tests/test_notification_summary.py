from datetime import datetime
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.services.notification_summary import build_daily_summary


class SummaryDb:
    def __init__(self, active_failed: bool, *, last_error: str = "active source error"):
        self.active_failed = active_failed
        self.last_error = last_error
        self.failure_queries = []

    def failed_sources(self, statement):
        sql = str(statement.compile(dialect=postgresql.dialect()))
        assert "sources.is_active IS true" in sql
        assert "sources.last_crawl_status =" in sql
        self.failure_queries.append(sql)
        return (
            [
                (
                    SimpleNamespace(
                        id=15,
                        url="https://example.org/source",
                        last_error=self.last_error,
                    ),
                    "Active source",
                )
            ]
            if self.active_failed else []
        )

    async def scalar(self, statement):
        sql = str(statement)
        if "FROM sources" in sql:
            return len(self.failed_sources(statement))
        return 0

    async def execute(self, statement):
        sql = str(statement)
        rows = self.failed_sources(statement) if "FROM sources" in sql else []
        return SimpleNamespace(
            all=lambda: rows,
            scalars=lambda: SimpleNamespace(all=lambda: rows),
        )


@pytest.mark.parametrize("active_failed", [False, True])
async def test_daily_summary_filters_disabled_sources_in_count_and_details(active_failed):
    db = SummaryDb(active_failed)
    summary = await build_daily_summary(
        db, since=datetime(2026, 10, 3), lookback_hours=24,
    )
    assert len(db.failure_queries) == 2
    assert summary.metrics["failed_sources"] == int(active_failed)
    assert f"当前失败来源 {int(active_failed)} 个。" in summary.message
    assert ("Active source" in summary.message) is active_failed
    assert ("最近失败原因" in summary.message) is active_failed
    assert summary.metrics["new_reports"] == 0
    daily_summary_payload = summary.payload["daily_summary"]
    assert daily_summary_payload["failed_sources"] == int(active_failed)
    assert daily_summary_payload["lookback_hours"] == 24
    assert len(daily_summary_payload["failure_sources"]) == int(active_failed)

    if active_failed:
        assert daily_summary_payload["failure_sources"][0] == {
            "source_id": 15,
            "think_tank_name": "Active source",
            "source_url": "https://example.org/source",
            "reason": "active source error",
        }


async def test_daily_summary_uses_readable_source_error():
    error = (
        "ProgrammingError: <class 'asyncpg.exceptions.UndefinedColumnError'>: "
        'column "document_hash" of relation "crawl_candidates" does not exist '
        "[SQL: INSERT INTO crawl_candidates]"
    )
    summary = await build_daily_summary(
        SummaryDb(True, last_error=error),
        since=datetime(2026, 10, 3),
        lookback_hours=24,
    )

    assert (
        "Active source：数据库结构未同步：数据表 crawl_candidates "
        "缺少字段 document_hash。"
    ) in summary.message
    assert "ProgrammingError" not in summary.message
    assert summary.payload["daily_summary"]["failure_sources"][0]["reason"] == (
        "数据库结构未同步：数据表 crawl_candidates 缺少字段 document_hash。"
    )
