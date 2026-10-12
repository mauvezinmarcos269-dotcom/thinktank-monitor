# 提交前分组审计

日期：2026-10-11

本文用于把当前工作区的大批未提交改动按主题拆分，避免教师端脚本、通知 payload、LLM 授权、采集解析、前端 UI 等改动混在同一个提交里。当前工作区存在 staged 与 unstaged 混合状态，提交前应先重新整理暂存区。

教师端脚本与文档这一组的具体 `git add` 候选清单见
[teacher-local-commit-prep-20261011.md](teacher-local-commit-prep-20261011.md)。

## 一、当前暂存区风险

`git status --short` 显示存在：

- `MM README.md`
- `MM docs/deployment-maintenance.md`
- `MM docs/teacher-local-user-guide.md`
- `AM scripts/teacher-local-diagnostics.ps1`
- `M  .gitignore`

含义是部分文件已经有旧内容被 staged，同时工作区又有新修改。建议正式提交前先执行一次人工复核：

```powershell
git diff --cached --name-status
git diff --name-status
```

如决定重新按主题提交，建议先取消暂存，再按组重新 `git add`：

```powershell
git restore --staged README.md docs/deployment-maintenance.md docs/teacher-local-user-guide.md scripts/teacher-local-diagnostics.ps1 .gitignore
```

不要使用 `git reset --hard`，当前工作区包含大量已完成但未提交的工作。

## 二、建议提交顺序

建议拆成 8 组，从低风险基础设施到业务功能逐步提交。

### 1. 教师端本地脚本与文档

建议提交说明：

```text
Improve teacher local Docker diagnostics and startup docs
```

主要文件：

- `scripts/teacher-local-docker.ps1`
- `scripts/teacher-local-start.ps1`
- `scripts/teacher-local-status.ps1`
- `scripts/teacher-local-health.ps1`
- `scripts/teacher-local-diagnostics.ps1`
- `scripts/teacher-local-stop.ps1`
- `scripts/teacher-local-backup.ps1`
- `scripts/teacher-local-update.ps1`
- `scripts/teacher-local-restore.ps1`
- `docs/teacher-local-startup-checklist.md`
- `docs/teacher-local-acceptance-20261011.md`
- `docs/teacher-local-user-guide.md`
- `docs/deployment-maintenance.md`
- `README.md`

已验证：

- Docker pipe `permission denied` 下，`health/status/start/stop/backup/update/restore/diagnostics` 失败路径无 PowerShell 堆栈。
- `backup` 失败时不再创建空备份目录。
- `restore` 在备份目录缺失、SQL 文件缺失、Docker 不可用时均不会进入危险恢复流程。
- PowerShell 语法解析和 Windows PowerShell 解析通过。
- `local-diagnostics-test`、`local-backups-test`、`local-restore-test` 已清理。

仍需补测：

- Docker Desktop 权限恢复后，补测真实启动、健康检查通过、备份、恢复和更新完整流程。

### 2. 本地端口与 PowerShell `-NoProfile` 口径

建议提交说明：

```text
Align local ports and PowerShell startup commands
```

主要文件：

- `scripts/start-local-backend.ps1`
- `scripts/start-local-frontend.ps1`
- `frontend/.env.local.example`
- `frontend/lib/api.ts`
- `frontend/package.json`
- `Makefile`
- `README.md`
- `docs/development.md`
- `docs/deployment-maintenance.md`
- `docs/teacher-local-user-guide.md`
- `docs/handoff-summary-20260929.md`
- `docs/llm-authorization-deployment-acceptance-20261005.md`
- `docs/source-onboarding-audit-20260915.md`

已验证：

- 前端默认 API 端口统一为 `8000`。
- 文档和脚本示例统一为 `powershell -NoProfile -ExecutionPolicy Bypass ...`。
- 生产构建曾在提升权限后通过；本轮未重复构建。

注意：

- 这一组和教师端文档有文件交叉，提交时可选择合并到第 1 组，或用 `git add -p` 精细拆分。

### 3. 通知 payload 与每日摘要来源链接

建议提交说明：

```text
Add structured notification payloads for daily summaries
```

主要文件：

- `backend/alembic/versions/d9f1a2c3b4e5_add_notification_payload.py`
- `backend/app/models/notification.py`
- `backend/app/schemas/notification.py`
- `backend/app/services/notification_summary.py`
- `backend/app/services/notification_service.py`
- `backend/tests/test_notification_summary.py`
- `backend/tests/test_notification_service.py`
- `frontend/lib/notification.ts`
- `frontend/app/notifications/page.tsx`
- `frontend/app/globals.css`

已验证：

- `poetry run pytest tests/test_notification_summary.py tests/test_notification_service.py` 通过。
- 相关 Ruff、typecheck、eslint 通过。
- 前端构建在提升权限后通过。
- Alembic 已升级到 `d9f1a2c3b4e5 (head)`。
- 前端通知页链接到设置页来源健康锚点的人工走查通过。

注意：

- 需要确认生产库迁移窗口。
- `frontend/app/globals.css` 同时含其他 UI 改动，可能需要 `git add -p`。

### 4. LLM 授权边界与默认不外发

建议提交说明：

```text
Add LLM authorization gates and default outbound safeguards
```

主要文件：

- `backend/alembic/versions/c8e4a6d91203_add_llm_authorizations.py`
- `backend/app/api/v1/llm_authorizations.py`
- `backend/app/core/llm_authorization.py`
- `backend/app/models/llm_authorization.py`
- `backend/app/schemas/llm_authorization.py`
- `backend/app/services/llm_authorization_service.py`
- `backend/app/core/config.py`
- `backend/app/core/llm.py`
- `backend/app/main.py`
- `backend/app/api/v1/reports.py`
- `backend/app/services/ai/*`
- `backend/app/workers/ai_tasks.py`
- `frontend/components/llm-authorization-control.tsx`
- `frontend/lib/llm-authorization.ts`
- `docs/llm-authorization-implementation-20261004.md`
- `docs/llm-authorization-deployment-acceptance-20261005.md`
- `docs/teacher-ai-boundary-audit-20261004.md`

已验证：

- 历史工作中已完成“默认不外发、涉华抽样与全文生成分别授权”的主流程和多轮确认。
- 本轮未重新运行该组完整测试。

注意：

- 这一组涉及数据库迁移、API、前端授权控件和 worker，提交前建议重新跑 LLM 授权相关测试。

### 5. 采集调度、锁、错误摘要与候选跳过原因

建议提交说明：

```text
Improve crawl scheduling diagnostics and candidate error summaries
```

主要文件：

- `backend/app/services/crawl_lock.py`
- `backend/app/services/crawl_error_summary.py`
- `backend/app/services/report_error_summary.py`
- `backend/app/services/candidate_skip_reason.py`
- `backend/app/services/crawl_candidate_service.py`
- `backend/app/services/crawl_quality_service.py`
- `backend/app/services/crawler/candidate_intake.py`
- `backend/app/services/crawler/candidate_duplicate_service.py`
- `backend/app/services/crawler/report_candidate_filter.py`
- `backend/app/services/crawler_service.py`
- `backend/app/workers/crawl_tasks.py`
- `backend/tests/test_crawl_lock.py`
- `backend/tests/test_crawl_error_summary.py`
- `backend/tests/test_report_error_summary.py`
- `backend/tests/test_candidate_duplicate_service.py`
- `backend/tests/test_candidate_intake.py`
- `backend/tests/test_crawl_scheduling.py`
- `frontend/components/processing-error-disclosure.tsx`
- `frontend/lib/crawl-error.ts`
- `frontend/lib/report-error.ts`
- `docs/schedule-notification-audit-20261004.md`

已验证：

- 历史工作中已验收定时采集与提醒链路、跳过展示和候选详情相关路径。
- 本轮未重新跑后端全量测试。

注意：

- 这一组和设置页 UI 改动、来源健康展示有交叉。

### 6. PDF/文档发现与解析器修复

建议提交说明：

```text
Expand PDF discovery and document extraction handling
```

主要文件：

- `backend/app/services/crawler/content_extractor.py`
- `backend/app/services/crawler/report_document_service.py`
- `backend/app/services/crawler/source_article_discovery.py`
- `backend/app/services/crawler/us_core_parser.py`
- `backend/app/scripts/audit_source_documents.py`
- `backend/app/scripts/pilot_crawl_sources.py`
- `backend/tests/test_content_extractor.py`
- `backend/tests/test_report_document_service.py`
- `backend/tests/test_us_core_parser.py`
- `backend/tests/test_audit_source_documents.py`
- `docs/source-onboarding-audit-20260915.md`
- `docs/source-rollout-status.md`
- `docs/rss-entry-audit-20261002.md`

已验证：

- 历史工作中已处理 RAND、Atlantic Council、Guardian Tiger III、PDF 报告发现入口和短 PDF 跳过展示。
- 本轮未重新跑采集脚本。

注意：

- 涉及真实站点抓取逻辑，提交前建议至少跑对应 parser 单测。

### 7. 前端报告页、设置页和轮询 UI 整理

建议提交说明：

```text
Refine report and settings UI workflows
```

主要文件：

- `frontend/app/reports/*`
- `frontend/app/settings/*`
- `frontend/app/dashboard/page.tsx`
- `frontend/app/layout.tsx`
- `frontend/components/app-shell.tsx`
- `frontend/lib/status.ts`
- `frontend/lib/use-notification-polling.ts`
- `frontend/public/favicon.svg`
- `frontend/app/globals.css`
- `frontend/app/settings/use-*.ts`

已验证：

- 历史工作中已做 Atlantic Council 最新 crawl run 页面走查和设置页来源错误展示修复。
- 本轮未重新运行前端截图/浏览器走查。

注意：

- `globals.css` 和 report/settings 页面变动较多，建议与通知 payload UI 分开提交或用 `git add -p`。

### 8. AI 字段、报告服务与 worker 管线

建议提交说明：

```text
Update AI report fields and worker processing flow
```

主要文件：

- `backend/alembic/versions/e038b9014347_add_ai_fields.py`
- `backend/app/services/ai/report_ai_chunk_runner.py`
- `backend/app/services/ai/report_ai_chunk_service.py`
- `backend/app/services/ai/report_ai_finalizer.py`
- `backend/app/services/ai/report_ai_finalizer_runner.py`
- `backend/app/services/ai/report_ai_service.py`
- `backend/app/services/ai/report_relevance_service.py`
- `backend/app/workers/report_tasks.py`
- `backend/app/workers/celery_app.py`
- `backend/app/workers/ai_tasks.py`
- `backend/app/services/dashboard_service.py`
- `backend/tests/test_ai_fields_migration.py`
- `backend/tests/test_report_service.py`
- `backend/tests/test_report_document_service.py`

已验证：

- 历史工作中已完成多篇受控试写、AI 生成授权与报告复核。
- 本轮未重新跑该组测试。

注意：

- 与 LLM 授权组存在交叉；如果提交边界难切，建议先把授权基础设施提交，再提交 AI 管线调整。

## 三、提交前建议检查

按组提交前建议至少运行：

```powershell
git status --short
git diff --check
```

后端相关组建议运行对应测试：

```powershell
cd backend
poetry run pytest tests/test_notification_summary.py tests/test_notification_service.py
poetry run pytest tests/test_llm_authorization.py tests/test_llm_authorization_api.py tests/test_llm_authorization_migration.py
poetry run pytest tests/test_crawl_lock.py tests/test_crawl_scheduling.py
```

前端相关组建议运行：

```powershell
cd frontend
npm run typecheck
npm exec eslint -- app/notifications/page.tsx lib/notification.ts
npm run build
```

教师端脚本组建议运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-health.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-status.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-start.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-diagnostics.ps1 -OutputRoot local-diagnostics-test -LogTail 20
```

如果 Docker Desktop 权限仍失败，只验证失败路径；不要把失败当作服务启动失败。

## 四、不要混入提交的内容

- `.codex-backups/` 只作本地备份，不提交。
- `local-diagnostics-test/`、`local-backups-test/`、`local-restore-test/` 已清理，不应提交。
- `frontend/.env.local` 是本地配置，不应提交。
- 真实老师数据库备份、诊断包和 `.env` 文件不应提交。
