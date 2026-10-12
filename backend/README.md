# ThinkTank Monitor Backend

全球智库涉华研究追踪平台后端 API 与任务系统

## 技术栈

- FastAPI
- PostgreSQL
- Redis
- Celery
- MinIO
- SQLAlchemy 2.x
- Alembic
- Pytest
- Ruff

## 目录说明

```text
app/
├── api/        # FastAPI 路由与依赖
├── core/       # 配置、日志、安全、LLM 客户端
├── db/         # 数据库会话
├── models/     # SQLAlchemy ORM 模型
├── schemas/    # Pydantic 入参和响应模型
├── scripts/    # 手动运维脚本，不自动执行
├── services/   # 业务服务、抓取、AI、导出逻辑
└── workers/    # Celery app 与异步任务
```

## 本地检查

```powershell
poetry run ruff check .
poetry run pytest
```

## 模型写法约定

- 新增或整理 ORM 模型时使用 SQLAlchemy 2.x 的 `Mapped[...]` 和 `mapped_column(...)`。
- 字段名、表名、索引和约束调整必须配套 Alembic 迁移。
- 仅做代码风格统一时不要改变数据库结构。
- `app/scripts/` 下的脚本用于人工诊断和运维，避免命名为 `test_*.py`。

## 通知任务

`app.workers.notification_tasks.daily_summary_task` 会生成每日站内摘要。
外发邮件、企业微信和飞书通知通过环境变量配置；未配置时自动跳过外发。
