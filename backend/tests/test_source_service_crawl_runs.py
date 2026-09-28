from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1 import sources as sources_api
from app.core.status import CrawlRunStatus
from app.models.source import CrawlStatusEnum, SourceTypeEnum
from app.models.think_tank import PriorityTierEnum, RegionFocusEnum
from app.schemas.institution import SourceCreate
from app.services.source_service import SourceService


class _FakeDb:
    async def get(self, model: type, object_id: int) -> object | None:
        return None


class _FakeExecuteRows:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows


class _FakeExecuteScalars:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def scalars(self) -> "_FakeExecuteRows":
        return _FakeExecuteRows(self._rows)


class _FakeHealthDb:
    def __init__(self, source: object, crawl_run: object) -> None:
        self._source = source
        self._crawl_run = crawl_run
        self._execute_count = 0

    async def execute(self, statement: object) -> object:
        self._execute_count += 1

        if self._execute_count == 1:
            return _FakeExecuteRows(
                [
                    (
                        self._source,
                        "rand",
                        "RAND Corporation",
                        "美国",
                        PriorityTierEnum.p0,
                        RegionFocusEnum.us,
                        True,
                        0,
                        None,
                    )
                ]
            )

        return _FakeExecuteScalars([self._crawl_run])


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


@pytest.mark.asyncio
async def test_get_health_uses_latest_crawl_quality_summary_for_diagnosis() -> None:
    now = datetime(2026, 9, 28, 12, 0, 0)
    source = SimpleNamespace(
        id=8,
        think_tank_id=3,
        source_type=SourceTypeEnum.website,
        url="https://example.org/research",
        crawl_frequency_minutes=1440,
        is_active=True,
        last_crawl_status=CrawlStatusEnum.success,
        last_crawled_at=now,
        last_error=None,
        created_at=now,
        updated_at=now,
    )
    crawl_run = SimpleNamespace(
        id=11,
        source_id=8,
        status=CrawlRunStatus.success,
        found_count=3,
        saved_count=0,
        error="质量检查：原始候选 3 条；有效去重后 3 条；入库 0 条；跳过：非涉华 3 条",
        started_at=now,
        finished_at=now + timedelta(seconds=6),
        created_at=now,
    )

    result = await SourceService().get_health(
        _FakeHealthDb(source, crawl_run),  # type: ignore[arg-type]
    )

    item = result.items[0]
    assert item.diagnosis_code == "non_china_candidates"
    assert item.diagnosis_label == "候选未通过涉华判断"
    assert item.recent_crawl_runs[0].error == crawl_run.error


@pytest.mark.asyncio
async def test_create_source_returns_404_when_think_tank_missing() -> None:
    payload = SourceCreate(
        source_type=SourceTypeEnum.rss,
        url="https://example.org/feed.xml",
    )

    with pytest.raises(HTTPException) as exc_info:
        await SourceService().create(
            _FakeDb(),  # type: ignore[arg-type]
            999,
            payload,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "智库机构不存在。"


@pytest.mark.asyncio
async def test_trigger_source_crawl_returns_503_when_queue_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSourceService:
        async def get_by_id(self, db: object, source_id: int) -> object:
            return SimpleNamespace(
                is_active=True,
                source_type=SourceTypeEnum.rss,
            )

    class FakeTask:
        @staticmethod
        def delay(source_id: int) -> object:
            raise RuntimeError("redis unavailable")

    monkeypatch.setattr(
        sources_api,
        "source_service",
        FakeSourceService(),
    )
    monkeypatch.setattr(
        sources_api,
        "crawl_source_task",
        FakeTask(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await sources_api.trigger_source_crawl(
            1,
            object(),  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "任务队列不可用，请检查 Celery 和 Redis 服务。"
