# 开发文档

本文档记录 ThinkTank Monitor 的日常开发约定，方便后续继续扩展抓取、通知、AI 处理和前端管理闭环。

## 分支与提交

- 当前主开发分支为 `feature/frontend`。
- 每次改动前先查看 `git status --short --branch`，确认是否存在他人或上一步遗留改动。
- 功能开发完成后先运行后端和前端检查，再提交。
- 不要把本地 `.env`、临时输出、备份目录、构建产物提交到仓库。

## 基线整理

阶段性功能完成后，先把工作区按以下口径整理为可回退基线：

- 应提交：业务代码、数据库迁移、测试、正式开发文档、来源治理文档和可复用脚本。
- 不提交：`docs/backups/`、`backend/docs/backups/`、`docs/exports/`、`backend/docs/exports/`、`.codex-backups/`、本地构建产物和本地密钥。
- 需人工确认：大体量样本数据、一次性诊断输出、面向老师交付的 Word/Markdown 成果，以及只在本地使用的临时脚本。
- 提交前运行 `git status --short --branch`，确认未跟踪文件中没有误加入备份、导出成果或敏感配置。

## 后端开发

常用命令：

```powershell
cd backend
poetry run ruff check .
poetry run pytest
```

ORM 模型统一使用 SQLAlchemy 2.x 写法：

```python
id: Mapped[int] = mapped_column(
    Integer,
    primary_key=True,
)
```

注意事项：

- 仅统一模型写法时，不改变字段类型、索引、约束和默认值。
- 修改表结构必须新增 Alembic migration。
- 服务层放业务逻辑，路由层只做鉴权、参数接收和响应返回。
- Celery task 尽量调用 service，避免在 task 文件里堆复杂 SQL。
- 手动诊断脚本放在 `backend/app/scripts/`，避免命名为 `test_*.py`。

本地手动运行 `backend/app/scripts/` 下的诊断、爬虫或 AI 运维脚本时，
统一通过仓库根目录的包装脚本执行，避免直接读取 Docker 环境中的
`redis` 主机名：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run-local-backend-command.ps1 poetry run python -m app.scripts.pilot_crawl_sources --help
```

包装脚本默认使用本地隔离队列 `thinktank-local-codex`；如果确认要投递给
当前 Docker worker 消费的 `celery` 队列，再显式传入 `-Queue celery`。

## 抓取与候选报告

- RSS 稳定性逻辑在 `backend/app/services/crawler/rss_parser.py`。
- 美国核心网站解析器在 `backend/app/services/crawler/us_core_parser.py`。
- “重磅报告”预筛规则在 `backend/app/services/crawler/report_candidate_filter.py`。
- 候选报告统计和导出由 `CrawlCandidateService` 提供。
- 单个来源的接入、试抓、前端复核、升级和停用流程见 `docs/source-onboarding-playbook.md`。

新增解析器时建议同步补充：

- 单元测试
- `docs/parser-priority.md`
- 来源健康或候选报告相关验证

## 通知与摘要

站内通知由 `NotificationService` 创建。每日摘要由 Celery beat 调度：

```text
notification.daily_summary
```

相关环境变量：

- `NOTIFICATION_DAILY_SUMMARY_ENABLED`
- `NOTIFICATION_SUMMARY_LOOKBACK_HOURS`
- `NOTIFICATION_INSTANT_ALERTS_ENABLED`
- `NOTIFICATION_EMAIL_ENABLED`
- `NOTIFICATION_EMAIL_TO`
- `NOTIFICATION_SMTP_HOST`
- `NOTIFICATION_SMTP_PORT`
- `NOTIFICATION_SMTP_USERNAME`
- `NOTIFICATION_SMTP_PASSWORD`
- `NOTIFICATION_SMTP_FROM`
- `NOTIFICATION_WECOM_WEBHOOK_URL`
- `NOTIFICATION_FEISHU_WEBHOOK_URL`

默认只生成站内通知；配置邮件或 webhook 后才会外发。即时外发默认关闭，
开启 `NOTIFICATION_INSTANT_ALERTS_ENABLED` 后，只对 P0/P1 来源的新报告
入库和 AI 成果完成事件即时外发，避免调试和批量抓取阶段频繁打扰老师。

## 前端开发

常用命令：

```powershell
cd frontend
npm run typecheck
npm run lint
npm run build
```

约定：

- API 类型和请求封装放在 `frontend/lib/`。
- 页面尽量复用现有 `panel`、`stats-grid`、`badge`、`table-wrap` 等样式。
- 仪表盘入口为 `frontend/app/dashboard/page.tsx`，数据来自 `/api/v1/dashboard`。
- 设置页负责来源健康、抓取运行、候选报告明细和导出闭环。

## 发布前检查清单

- 后端 `ruff` 和 `pytest` 通过。
- 前端 `typecheck`、`lint`、`build` 通过。
- `git diff --check` 无尾随空白。
- `git status --short` 中没有误加入的备份、密钥、构建产物或临时脚本。
