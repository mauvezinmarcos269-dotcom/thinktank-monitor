# 开发文档

本文档记录 ThinkTank Monitor 的日常开发约定，方便后续继续扩展抓取、通知、AI 处理和前端管理闭环。

## 分支与提交

- 当前主开发分支为 `feature/frontend`。
- 每次改动前先查看 `git status --short --branch`，确认是否存在他人或上一步遗留改动。
- 功能开发完成后先运行后端和前端检查，再提交。
- 不要把本地 `.env`、临时输出、备份目录、构建产物提交到仓库。

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

## 抓取与候选报告

- RSS 稳定性逻辑在 `backend/app/services/crawler/rss_parser.py`。
- 美国核心网站解析器在 `backend/app/services/crawler/us_core_parser.py`。
- “重磅报告”预筛规则在 `backend/app/services/crawler/report_candidate_filter.py`。
- 候选报告统计和导出由 `CrawlCandidateService` 提供。

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
- `NOTIFICATION_EMAIL_ENABLED`
- `NOTIFICATION_EMAIL_TO`
- `NOTIFICATION_SMTP_HOST`
- `NOTIFICATION_SMTP_PORT`
- `NOTIFICATION_SMTP_USERNAME`
- `NOTIFICATION_SMTP_PASSWORD`
- `NOTIFICATION_SMTP_FROM`
- `NOTIFICATION_WECOM_WEBHOOK_URL`
- `NOTIFICATION_FEISHU_WEBHOOK_URL`

默认只生成站内通知；配置邮件或 webhook 后才会外发。

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
