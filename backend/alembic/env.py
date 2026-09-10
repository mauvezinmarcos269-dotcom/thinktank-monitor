import asyncio
from logging.config import fileConfig
from typing import Any

from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config import settings
from app.models import Base

# Alembic Config 对象，来自 alembic.ini。
config = context.config


# 配置 Alembic 日志。
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# 必须导入全部 SQLAlchemy 模型后再获取 metadata。
# app.models.__init__.py 已导入 User，因此 users 表能被 Alembic 发现。
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    离线模式：
    不实际连接数据库，只生成 SQL 文本。

    使用示例：
        alembic upgrade head --sql
    """
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    在同步 Connection 上配置并执行迁移。

    虽然项目数据库引擎是 async engine，
    但 Alembic 的迁移执行逻辑通过 connection.run_sync()
    切换到这里的同步上下文。
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    在线模式：
    连接 PostgreSQL 并实际执行迁移。
    """
    configuration: dict[str, Any] = config.get_section(
        config.config_ini_section
    ) or {}

    # alembic.ini 中的 sqlalchemy.url 仅是占位符；
    # 运行时必须以 .env / Docker 环境变量中的真实 URL 覆盖。
    configuration["sqlalchemy.url"] = settings.DATABASE_URL

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
