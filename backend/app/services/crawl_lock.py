from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import func, select

from app.db.session import engine

CRAWL_BATCH_LOCK_NAMESPACE = 0x544B4D
CRAWL_SOURCE_LOCK_NAMESPACE = 0x544B4E


@asynccontextmanager
async def crawl_execution_lock(source_id: int | None = None) -> AsyncIterator[bool]:
    namespace = (
        CRAWL_BATCH_LOCK_NAMESPACE
        if source_id is None
        else CRAWL_SOURCE_LOCK_NAMESPACE
    )
    # A dedicated transaction keeps the lock across crawl-session commits.
    # PostgreSQL releases it on rollback, disconnect or worker termination.
    async with engine.connect() as connection:
        async with connection.begin():
            acquired = bool(
                await connection.scalar(
                    select(func.pg_try_advisory_xact_lock(namespace, source_id or 0))
                )
            )
            yield acquired
