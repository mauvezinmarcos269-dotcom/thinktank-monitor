from datetime import datetime
from types import SimpleNamespace

import pytest

from app.core.status import AIChunkStatus
from app.services.ai.report_ai_chunk_service import (
    recover_stale_report_ai_chunk,
)


class _FakeScalarResult:
    def __init__(self, value: object | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object | None:
        return self.value


class _FakeChunkDb:
    def __init__(self, chunk: object) -> None:
        self.chunk = chunk
        self.flushed = False

    async def execute(self, statement: object) -> _FakeScalarResult:
        return _FakeScalarResult(self.chunk)

    async def flush(self) -> None:
        self.flushed = True


@pytest.mark.asyncio
async def test_recover_stale_ai_chunk_treats_missing_queued_timestamp_as_stale() -> None:
    chunk = SimpleNamespace(
        status=AIChunkStatus.queued.value,
        updated_at=None,
        retry_count=0,
        last_error=None,
    )
    db = _FakeChunkDb(chunk)

    recovered = await recover_stale_report_ai_chunk(
        db,  # type: ignore[arg-type]
        12,
        queued_stale_before=datetime(2026, 9, 28, 10, 0, 0),
        processing_stale_before=datetime(2026, 9, 28, 10, 0, 0),
    )

    assert recovered is chunk
    assert chunk.status == AIChunkStatus.pending.value
    assert chunk.retry_count == 0
    assert chunk.last_error == "Stale queued AI chunk recovered"
    assert chunk.updated_at is not None
    assert db.flushed is True


@pytest.mark.asyncio
async def test_recover_stale_ai_chunk_treats_missing_processing_timestamp_as_stale() -> None:
    chunk = SimpleNamespace(
        status=AIChunkStatus.processing.value,
        updated_at=None,
        retry_count=1,
        last_error=None,
    )
    db = _FakeChunkDb(chunk)

    recovered = await recover_stale_report_ai_chunk(
        db,  # type: ignore[arg-type]
        12,
        queued_stale_before=datetime(2026, 9, 28, 10, 0, 0),
        processing_stale_before=datetime(2026, 9, 28, 10, 0, 0),
    )

    assert recovered is chunk
    assert chunk.status == AIChunkStatus.failed.value
    assert chunk.retry_count == 2
    assert chunk.last_error == "Stale processing AI chunk recovered"
    assert chunk.updated_at is not None
    assert db.flushed is True
