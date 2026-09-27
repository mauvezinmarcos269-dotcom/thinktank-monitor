from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1 import sources as sources_api
from app.models.source import SourceTypeEnum
from app.schemas.institution import SourceCreate
from app.services.source_service import SourceService


class _FakeDb:
    async def get(self, model: type, object_id: int) -> object | None:
        return None


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
