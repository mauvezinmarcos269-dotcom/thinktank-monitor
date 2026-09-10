# ThinkTank Monitor

ThinkTank Monitor 是一个面向智库研究报告的实时监测、采集、翻译和分析平台。

系统主要用于：

- 接入国内外智库、研究机构和政府机构网站
- 自动采集研究报告、政策简报和评论文章
- 对报告进行去重、归档和全文保存
- 调用大语言模型生成翻译和分析评论
- 支持按照标题、来源、发布时间和分析状态检索报告
- 为教师和管理员提供统一的监测仪表盘

## 技术栈

### 后端

- Python
- FastAPI
- SQLAlchemy Async
- PostgreSQL
- Redis
- Celery
- MinIO
- JWT

### 前端

- Next.js
- React
- TypeScript

## 项目结构

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── alembic/
│   ├── requirements.txt
│   └── README.md
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── package.json
├── docker-compose.yml
├── Makefile
└── README.md
```

## 本地联调

本地联调建议使用独立端口和独立 Celery 队列，避免与 Docker
中的 worker 抢同一批任务。

在三个 PowerShell 窗口分别运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-local-backend.ps1
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-local-worker.ps1
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-local-frontend.ps1
```

默认地址：

- 后端：`http://127.0.0.1:8001`
- 前端：`http://localhost:3001`
- Redis：`redis://127.0.0.1:6379/0`
- 本地 Celery 队列：`thinktank-local-codex`
- 本地 Celery 结果库：`redis://127.0.0.1:6379/1`

如果 Docker worker 正在运行，它默认只消费 `celery` 队列；
本地后端和本地 worker 默认使用 `thinktank-local-codex` 队列，
两者不会互相抢任务。

如果你怀疑还有旧 worker 在同一个 Redis 上运行，可以显式指定队列：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-local-backend.ps1 -Queue thinktank-local-codex
powershell -ExecutionPolicy Bypass -File scripts/start-local-worker.ps1 -Queue thinktank-local-codex
```

### 前端构建注意事项

Next.js 的开发服务和生产构建都会写入 `frontend/.next`。
本地开发时不要在 `npm run dev -p 3001` 正在运行的同时执行
`npm run build`，否则可能造成开发缓存缺块，页面出现 500。

需要做生产构建检查时，先停止前端开发服务，再运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-local-frontend.ps1
```

或：

```powershell
cd frontend
npm run build:local
```

## Docker 运行

Docker 环境使用容器网络中的 Redis 地址：

- `redis://redis:6379/0`
- Docker Celery 队列：`celery`
- MinIO 服务地址：`minio:9000`

```bash
docker compose up -d
```

如果修改了后端、前端、worker、AI 或 Celery 配置，
需要重建相关 Docker 服务：

```bash
docker compose up -d --build backend celery-worker celery-beat frontend
```

### 部署前检查

- 确认 `.env` 和 `backend/.env` 中的密码、JWT 密钥、LLM Key 不使用示例值。
- 生产环境只开放必要端口；PostgreSQL、Redis、MinIO 控制台不建议直接暴露到公网。
- `BACKEND_CORS_ORIGINS` 只填写实际前端域名。
- 后端、Celery worker、Celery beat 和前端容器默认以非 root 用户运行。
- 前端依赖升级前先运行 `npm audit`，确认是否需要执行 `npm audit fix` 并重新验证构建。
