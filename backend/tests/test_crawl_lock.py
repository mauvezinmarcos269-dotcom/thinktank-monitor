import asyncio

import pytest

from app.services import crawl_lock


class FakeConnection:
    def __init__(self, held):
        self.held = held
        self.key = None
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        if self.key is not None:
            self.held.remove(self.key)
            self.key = None
        self.closed = True

    def begin(self):
        return self

    async def scalar(self, statement):
        compiled = statement.compile()
        assert "pg_try_advisory_xact_lock" in str(compiled)
        key = tuple(compiled.params.values())
        if key in self.held:
            return False
        self.held.add(key)
        self.key = key
        return True


@pytest.fixture
def lock_engine(monkeypatch):
    class FakeEngine:
        def __init__(self):
            self.held = set()
            self.connections = []

        def connect(self):
            connection = FakeConnection(self.held)
            self.connections.append(connection)
            return connection

    engine = FakeEngine()
    monkeypatch.setattr(crawl_lock, "engine", engine)
    return engine


async def test_locks_exclude_same_source_but_not_other_source_or_batch(lock_engine):
    async with crawl_lock.crawl_execution_lock(7) as first:
        assert first
        async with crawl_lock.crawl_execution_lock(7) as duplicate:
            assert not duplicate
        assert len(lock_engine.held) == 1
        async with crawl_lock.crawl_execution_lock(8) as other:
            assert other
        async with crawl_lock.crawl_execution_lock() as batch:
            assert batch
            async with crawl_lock.crawl_execution_lock() as duplicate_batch:
                assert not duplicate_batch
    assert lock_engine.held == set()
    assert all(connection.closed for connection in lock_engine.connections)
    async with crawl_lock.crawl_execution_lock(7) as recovered:
        assert recovered


async def test_lock_is_released_on_exception(lock_engine):
    with pytest.raises(RuntimeError, match="interrupted"):
        async with crawl_lock.crawl_execution_lock(7):
            raise RuntimeError("interrupted")
    assert lock_engine.held == set()
    async with crawl_lock.crawl_execution_lock(7) as recovered:
        assert recovered


async def test_lock_is_released_on_task_cancellation(lock_engine):
    started = asyncio.Event()

    async def hold_lock():
        async with crawl_lock.crawl_execution_lock(7) as acquired:
            assert acquired
            started.set()
            await asyncio.Future()

    task = asyncio.create_task(hold_lock())
    await asyncio.wait_for(started.wait(), timeout=1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert lock_engine.held == set()
    async with crawl_lock.crawl_execution_lock(7) as recovered:
        assert recovered
