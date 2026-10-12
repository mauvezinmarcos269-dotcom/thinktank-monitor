import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.dialects import postgresql

from app.core.status import CrawlRunStatus
from app.models import CrawlRun, Source, ThinkTank
from app.models.source import CrawlStatusEnum, SourceTypeEnum
from app.scripts import pilot_crawl_sources
from app.services import crawler_service
from app.workers.celery_app import celery_app
from app.workers.crawl_tasks import crawl_all_sources_task


def source(**changes):
    values = {
        "id": 7,
        "think_tank_id": 7,
        "is_active": True,
        "source_type": SourceTypeEnum.website,
        "crawl_frequency_minutes": 1440,
        "last_crawled_at": datetime.now(UTC) - timedelta(days=2),
        "last_crawl_status": CrawlStatusEnum.success,
        "last_error": None,
    }
    values.update(changes)
    return SimpleNamespace(**values)


class FakeDb:
    def __init__(self, item=None, key="rand", rows=()):
        self.source = item
        self.think_tank = SimpleNamespace(key=key)
        self.rows = rows
        self.statements = []
        self.added = []
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        pass

    async def get(self, model, _id):
        if model is Source:
            return self.source
        if model is ThinkTank:
            return self.think_tank
        assert model is CrawlRun
        return self.added[-1]

    async def execute(self, statement):
        self.statements.append(statement)
        return SimpleNamespace(all=lambda: self.rows)

    def add(self, item):
        item.id = 90
        self.added.append(item)

    async def commit(self):
        self.commits += 1

    async def refresh(self, item):
        pass


@pytest.fixture
def held_locks(monkeypatch):
    held = set()

    @asynccontextmanager
    async def lock(source_id=None):
        acquired = source_id not in held
        if acquired:
            held.add(source_id)
        try:
            yield acquired
        finally:
            if acquired:
                held.remove(source_id)

    monkeypatch.setattr(crawler_service, "crawl_execution_lock", lock)
    monkeypatch.setattr(pilot_crawl_sources, "crawl_execution_lock", lock)
    return held


def test_beat_checks_every_five_minutes_without_daily_duplicate():
    entries = [
        entry for entry in celery_app.conf.beat_schedule.values()
        if entry["task"] == "crawl.all_sources"
    ]
    assert len(entries) == 1
    assert entries[0]["schedule"].minute == set(range(0, 60, 5))
    assert entries[0]["schedule"].hour == set(range(24))
    assert entries[0]["options"]["expires"] == 300


def test_daily_frequency_becomes_due_on_next_poll_not_next_day():
    finished = datetime(2026, 10, 1, 10, 2, tzinfo=UTC)
    item = source(last_crawled_at=finished)
    next_day = finished + timedelta(days=1)
    assert not crawler_service._is_source_due_for_crawl(
        item, now=next_day.replace(minute=0)
    )
    assert crawler_service._is_source_due_for_crawl(
        item, now=next_day.replace(minute=5)
    )
    assert item.crawl_frequency_minutes == 1440


async def test_due_selection_filters_rollout_and_preserves_stale_running_recovery(monkeypatch):
    db = FakeDb(rows=[
        (source(id=1), "brookings"),
        (source(id=2), "new_source"),
        (source(id=3), "heritage"),
        (source(id=4, last_crawled_at=datetime.now(UTC)), "rand"),
        (source(id=5, last_crawl_status=CrawlStatusEnum.running), "rand"),
    ])
    monkeypatch.setattr(crawler_service, "AsyncSessionLocal", lambda: db)
    assert await crawler_service._get_due_source_ids() == [1, 5]
    compiled = db.statements[0].compile(dialect=postgresql.dialect())
    assert "sources.is_active IS true" in str(compiled)
    assert "sources.source_type IN" in str(compiled)
    assert [SourceTypeEnum.rss, SourceTypeEnum.website] in compiled.params.values()
    assert "JOIN think_tanks" in str(compiled)
    assert "NULLS FIRST" in str(compiled)


@pytest.mark.parametrize(
    ("changes", "key", "expected"),
    [
        ({"is_active": False}, "rand", "source_disabled"),
        ({"source_type": SourceTypeEnum.topic_page}, "rand", "unsupported_source_type"),
        ({}, "new_source", "rollout_not_allowed"),
        ({}, "heritage", "rollout_not_allowed"),
        ({"last_crawled_at": datetime.now(UTC)}, "rand", "not_due"),
    ],
)
async def test_scheduled_execution_rechecks_after_acquiring_lock(
    monkeypatch, held_locks, changes, key, expected,
):
    db = FakeDb(source(**changes), key=key)

    def session():
        assert 7 in held_locks
        return db

    fetch = AsyncMock(side_effect=AssertionError("Must not fetch"))
    monkeypatch.setattr(crawler_service, "AsyncSessionLocal", session)
    monkeypatch.setattr(crawler_service, "_fetch_source_articles", fetch)
    result = await crawler_service._crawl_source_async(7, only_if_due=True)
    assert result == crawler_service._skipped_source_result(7, expected)
    assert db.added == []
    assert db.commits == 0
    fetch.assert_not_awaited()


async def test_missing_source_is_skipped_without_writing(monkeypatch, held_locks):
    db = FakeDb()
    monkeypatch.setattr(crawler_service, "AsyncSessionLocal", lambda: db)
    result = await crawler_service._crawl_source_async(7, only_if_due=True)
    assert result["reason"] == "source_missing"
    assert db.commits == 0


@pytest.mark.parametrize("only_if_due", [False, True])
async def test_busy_source_never_enters_crawl(monkeypatch, held_locks, only_if_due):
    held_locks.add(7)
    execute = AsyncMock(side_effect=AssertionError("Must not enter crawl"))
    monkeypatch.setattr(crawler_service, "_crawl_source_locked_async", execute)
    result = await crawler_service._crawl_source_async(7, only_if_due=only_if_due)
    assert result["reason"] == "already_running"
    execute.assert_not_awaited()
    assert held_locks == {7}


@pytest.mark.parametrize("only_if_due", [False, True])
async def test_empty_crawl_completes_and_recovers_interrupted_runs(
    monkeypatch, held_locks, only_if_due,
):
    item = source(last_crawl_status=CrawlStatusEnum.running)
    if not only_if_due:
        item.last_crawled_at = datetime.now(UTC)
    db = FakeDb(item)

    async def fetch(_source):
        assert 7 in held_locks
        return []

    monkeypatch.setattr(crawler_service, "AsyncSessionLocal", lambda: db)
    monkeypatch.setattr(crawler_service, "_fetch_source_articles", fetch)
    result = await crawler_service._crawl_source_async(7, only_if_due=only_if_due)
    assert result["status"] == "success"
    assert result["saved_count"] == 0
    assert item.last_crawl_status == CrawlStatusEnum.success
    assert db.added[0].status == CrawlRunStatus.success.value
    assert db.commits == 2
    assert held_locks == set()
    recovery = db.statements[0].compile(dialect=postgresql.dialect())
    assert "UPDATE crawl_runs" in str(recovery)
    assert "crawl_runs.source_id =" in str(recovery)
    assert "crawl_runs.status =" in str(recovery)
    assert recovery.params["status"] == CrawlRunStatus.failed.value
    assert recovery.params["status_1"] == CrawlRunStatus.running.value
    assert item.crawl_frequency_minutes == 1440


async def test_crawl_failure_records_error_before_releasing_source_lock(monkeypatch, held_locks):
    db = FakeDb(source())

    async def fail(_source):
        assert 7 in held_locks
        raise RuntimeError("discovery failed")

    monkeypatch.setattr(crawler_service, "AsyncSessionLocal", lambda: db)
    monkeypatch.setattr(crawler_service, "_fetch_source_articles", fail)
    with pytest.raises(RuntimeError, match="discovery failed"):
        await crawler_service._crawl_source_async(7, only_if_due=True)
    assert db.added[0].status == CrawlRunStatus.failed.value
    assert db.source.last_crawl_status == CrawlStatusEnum.failed
    assert db.commits == 2
    assert held_locks == set()


async def test_overlapping_batches_are_skipped(monkeypatch, held_locks):
    started = asyncio.Event()
    release = asyncio.Event()

    async def crawl(source_id, *, only_if_due):
        assert only_if_due
        started.set()
        await release.wait()
        return {"status": "success", "saved_count": 1}

    select_due = AsyncMock(return_value=[7])
    monkeypatch.setattr(crawler_service, "_get_due_source_ids", select_due)
    monkeypatch.setattr(crawler_service, "_crawl_source_async", crawl)
    first = asyncio.create_task(crawler_service._crawl_all_sources_async())
    try:
        await asyncio.wait_for(started.wait(), timeout=1)
        second = await crawler_service._crawl_all_sources_async()
        assert second["status"] == "skipped"
        assert second["reason"] == "already_running"
        assert second["selected_count"] == 0
        select_due.assert_awaited_once()
    finally:
        release.set()
        result = await first
    assert result["saved_count"] == 1
    assert held_locks == set()


async def test_batch_reports_partial_failure_and_continues(monkeypatch, held_locks):
    async def crawl(source_id, *, only_if_due):
        assert only_if_due
        if source_id == 1:
            raise RuntimeError("fetch failed")
        if source_id == 2:
            return crawler_service._skipped_source_result(source_id, "not_due")
        return {"status": "success", "saved_count": 2}

    monkeypatch.setattr(crawler_service, "_get_due_source_ids", AsyncMock(return_value=[1, 2, 3]))
    monkeypatch.setattr(crawler_service, "_crawl_source_async", crawl)
    assert await crawler_service._crawl_all_sources_async() == {
        "status": "partial_failure",
        "selected_count": 3,
        "completed_count": 1,
        "skipped_count": 1,
        "failed_count": 1,
        "saved_count": 2,
    }


@pytest.mark.parametrize(("ids", "status"), [([], "success"), ([7], "failed")])
async def test_empty_or_failed_batch_status(monkeypatch, held_locks, ids, status):
    monkeypatch.setattr(crawler_service, "_get_due_source_ids", AsyncMock(return_value=ids))
    monkeypatch.setattr(crawler_service, "_crawl_source_async", AsyncMock(side_effect=RuntimeError))
    result = await crawler_service._crawl_all_sources_async()
    assert result["status"] == status
    assert result["failed_count"] == len(ids)


def test_celery_task_preserves_batch_summary(monkeypatch):
    result = {"status": "partial_failure", "failed_count": 1, "saved_count": 0}
    monkeypatch.setattr(crawler_service, "crawl_all_sources", lambda: result)
    assert crawl_all_sources_task.run() is result


async def test_pilot_crawl_shares_source_lock(monkeypatch, held_locks):
    pilot = pilot_crawl_sources.PilotSource(key="rand", name="RAND", source=source())
    execute = AsyncMock(return_value={"saved_count": 1})
    monkeypatch.setattr(pilot_crawl_sources, "_pilot_crawl_source_locked", execute)
    held_locks.add(7)
    options = {"max_saved": 1, "max_candidates": 5, "notify": False, "ai_status": "skipped"}
    result = await pilot_crawl_sources.pilot_crawl_source(pilot, **options)
    assert result["reason"] == "already_running"
    execute.assert_not_awaited()
    held_locks.remove(7)
    assert await pilot_crawl_sources.pilot_crawl_source(pilot, **options) == {"saved_count": 1}
    execute.assert_awaited_once_with(pilot, **options)
