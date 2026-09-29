# 部署与长期维护手册

更新时间：2026-09-29

本文用于把平台从本地开发推进到可长期运行的监测系统。当前建议先采用
“小批量、可复核、可回退”的部署策略，确认报告质量和提醒频率后，再扩大来源范围。

老师日常使用说明见 [teacher-local-user-guide.md](teacher-local-user-guide.md)。

## 一、部署组件

平台长期运行至少需要以下服务：

| 组件 | 作用 | 当前配置 |
| --- | --- | --- |
| PostgreSQL + pgvector | 保存用户、来源、候选、报告、AI 分块和通知 | `postgres` |
| Redis | Celery 队列、结果后端和缓存 | `redis` |
| MinIO | 后续保存 PDF、导出文件或原始文档 | `minio` |
| FastAPI backend | 后端 API 和鉴权 | `backend` |
| Celery worker | 抓取、正文提取、AI 处理、通知任务 | `celery-worker` |
| Celery beat | 定时抓取、AI 轮询、每日摘要 | `celery-beat` |
| Next.js frontend | 老师和管理员使用的页面 | `frontend` |

本地 Docker Compose 默认更偏开发环境：后端挂载源码并使用 `--reload`。如果部署到学院服务器或云服务器，建议改成生产口径：不挂载源码、不使用 `--reload`，通过镜像重建发布。

## 二、环境变量

部署前从 `.env.example` 复制并分别准备根目录 `.env` 和 `backend/.env`。不要提交真实 `.env`。

必须替换：

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `MINIO_ROOT_PASSWORD`
- `MINIO_SECRET_KEY`
- `JWT_SECRET_KEY`
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `BACKEND_CORS_ORIGINS`

可选配置：

- 邮件提醒：`NOTIFICATION_EMAIL_*`
- 企业微信提醒：`NOTIFICATION_WECOM_WEBHOOK_URL`
- 飞书提醒：`NOTIFICATION_FEISHU_WEBHOOK_URL`
- 即时外发：`NOTIFICATION_INSTANT_ALERTS_ENABLED`

初期建议：

- 保持 `NOTIFICATION_INSTANT_ALERTS_ENABLED=false`。
- 先使用站内通知和每日摘要。
- 等老师确认提醒噪声可接受后，再开启邮件或 webhook。

## 三、老师本地电脑部署建议

如果平台部署在老师本地电脑，推荐采用 Docker Desktop 方式运行，老师通过浏览器访问本机地址：

- 前端页面：`http://localhost:3000`
- 后端 API：`http://localhost:8000`
- MinIO 控制台：仅维护时打开 `http://localhost:9001`

本地部署原则：

1. 不暴露公网端口，避免数据库、Redis、MinIO 或后台 API 被外部访问。
2. `BACKEND_CORS_ORIGINS` 只保留 `http://localhost:3000` 和 `http://127.0.0.1:3000`。
3. PostgreSQL、Redis、MinIO 密码仍必须使用强密码，不能使用示例值。
4. 老师电脑休眠或关机时，定时抓取和 AI 任务会暂停；下次开机后再继续运行。
5. 初期只开启站内通知；外发邮件或 webhook 等老师确认后再配置。

老师本地电脑需要预装：

- Docker Desktop
- Git
- Node.js 和 Python 仅在需要本地开发时安装；如果只用 Docker 运行，可不让老师接触开发命令

建议日常启动方式：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/teacher-local-start.ps1
```

首次部署或更新代码后需要重建镜像时：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/teacher-local-start.ps1 -Build
```

建议日常停止方式：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/teacher-local-stop.ps1
```

建议查看运行状态：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/teacher-local-status.ps1
```

建议健康检查：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/teacher-local-health.ps1
```

维护者推送新版本后，老师电脑可一键更新：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/teacher-local-update.ps1
```

这个脚本默认会先备份，再拉取代码、重建服务、执行数据库迁移并运行健康检查。若只想重建当前目录代码，不执行 `git pull`，可加 `-SkipPull`。

建议查看后台日志：

```powershell
docker compose logs -f backend
docker compose logs -f celery-worker
docker compose logs -f celery-beat
```

如果希望开机后自动运行，可在 Windows 任务计划程序中创建任务，登录后执行：

```powershell
powershell -ExecutionPolicy Bypass -File "C:\path\to\thinktank-monitor\scripts\teacher-local-start.ps1"
```

其中 `C:\path\to\thinktank-monitor` 替换为老师电脑上的项目目录。

## 四、启动与迁移

本地联调：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-local-backend.ps1
powershell -ExecutionPolicy Bypass -File scripts/start-local-worker.ps1
powershell -ExecutionPolicy Bypass -File scripts/start-local-frontend.ps1
```

Docker 启动：

```bash
docker compose up -d --build
```

数据库迁移：

```bash
docker compose exec backend alembic upgrade head
```

创建管理员：

```bash
docker compose exec backend python -m app.scripts.create_superuser
```

常用检查：

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f celery-worker
docker compose logs -f celery-beat
```

## 五、定时任务

`celery-beat` 当前调度：

| 任务 | 时间 | 用途 |
| --- | --- | --- |
| `crawl.all_sources` | 每天 18:00 | 抓取到期来源 |
| `report.enqueue_ai_chunk_tasks` | 每 5 分钟 | 将 pending 报告投递给 AI 分块处理 |
| `notification.daily_summary` | 每天 19:00 | 生成每日通知摘要 |

注意：

- `pilot_crawl` 只表示允许小批量试运行，不等于全量自动化。
- 新增来源前必须先完成只读审计和人工复核。
- `blocked` 来源不得加入默认入库试运行命令。

## 六、日常巡检

建议每天或每次演示前检查：

1. 仪表盘是否有 AI 异常、来源需处理或未读提醒。
2. 报告页是否有 `pending_review`、`needs_rerun` 或 AI failed。
3. 设置页来源健康是否出现 failed、never、document gate failed。
4. `celery-worker` 是否持续消费任务。
5. `celery-beat` 是否按计划投递定时任务。
6. LLM 额度、Key、模型名是否可用。

建议每周记录：

- 新增报告数量。
- 复核通过率。
- 被跳过的主要原因。
- 来源失败原因。
- AI 失败或重跑原因。
- 老师对翻译稿和评论稿的修改意见。

## 七、备份策略

至少备份：

- PostgreSQL 数据库。
- MinIO 数据卷。
- `.env` 和 `backend/.env` 的安全副本。
- 老师已确认的导出成果。

老师本地电脑建议每周至少备份一次，备份文件放到移动硬盘、学院网盘或加密云盘。不要只放在同一台电脑上。

PostgreSQL 备份示例：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/teacher-local-backup.ps1
```

备份默认保存到 `local-backups/`，该目录已加入 `.gitignore`，不会被提交到代码仓库。
如果 MinIO 数据较大，可临时跳过 MinIO：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/teacher-local-backup.ps1 -SkipMinio
```

恢复前必须先备份当前库，避免误覆盖。

MinIO 数据建议通过服务器快照或数据卷备份统一处理。若后续大量保存 PDF 原文，MinIO 备份优先级应提高。

## 八、上线前清单

- 后端 `poetry run ruff check .` 通过。
- 后端 `poetry run pytest` 通过。
- 前端 `npm run typecheck` 通过。
- 前端 `npm run lint` 通过。
- 前端 `npm run build` 通过。
- `.env` 中没有示例密码或空的 JWT 密钥。
- `BACKEND_CORS_ORIGINS` 只包含真实前端域名。
- PostgreSQL、Redis、MinIO 控制台不直接暴露公网。
- 已创建管理员账号。
- 已确认提醒渠道和提醒频率。
- 已确认第一批稳定运行来源名单。

## 九、推荐运行节奏

第一阶段：

- 只运行已验证的 Brookings、CFR、CSIS、PIIE、AEI、ECFR。
- 每个来源保持每次最多新增 1 篇。
- AI 成果完成后必须前端人工复核。

第二阶段：

- 选择 RAND、Carnegie、Chatham House、Bruegel、JIIA 等做只读审计。
- 不直接自动入库。
- 通过样本复核后再更新 rollout 策略。

第三阶段：

- 配置邮件、企业微信或飞书提醒。
- 固化 Word 模板。
- 形成每周报告和来源健康摘要。
