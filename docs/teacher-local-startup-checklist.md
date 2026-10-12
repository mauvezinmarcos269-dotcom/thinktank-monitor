# 老师本地启动验收清单

更新时间：2026-10-11

本文用于老师电脑本地 Docker 运行的启动验收和常见故障分流。日常只需先运行启动脚本，再运行健康检查；如果健康检查失败，按本文对应症状处理。

本轮脚本与文档总体验收记录见
[teacher-local-acceptance-20261011.md](teacher-local-acceptance-20261011.md)。

## 一、标准启动与验收

在项目根目录依次运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-start.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-health.ps1
```

验收通过时，应满足：

1. Docker command、Docker Compose command、Docker daemon 均为 `[OK]`。
2. `postgres`、`redis`、`minio`、`backend`、`celery-worker`、`celery-beat`、`frontend` 容器均为 `running`。
3. Backend `/health` 返回 200。
4. Frontend page 返回 200。
5. Celery worker ping 为 `[OK]`。
6. 浏览器可以打开 `http://localhost:3000`。

如果以上任一项失败，不要反复点击页面刷新，先按下面四类问题分流。

## 二、Docker 未启动或权限不足

典型提示：

- `Docker Desktop is not reachable`
- `Docker pipe`
- `permission denied`
- `dockerDesktopLinuxEngine`
- `Docker daemon ... cannot access the Docker pipe`

处理顺序：

1. 打开 Docker Desktop，等待它完全启动。
2. 关闭当前 PowerShell，重新打开 PowerShell。
3. 回到项目根目录，再运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-health.ps1
```

如果仍提示 `permission denied`，请维护者用管理员 PowerShell 执行：

```powershell
net localgroup docker-users "$env:USERNAME" /add
```

执行后需要注销 Windows 并重新登录，再重新运行健康检查。这个问题通常不是平台代码错误，而是当前 Windows 用户没有 Docker Desktop 管道访问权限。

## 三、端口被占用

教师 Docker 模式需要：

- 前端端口：`3000`
- 后端端口：`8000`

典型提示：

- `port 3000 is already listening`
- `port 8000 is already listening`
- 页面打不开，但健康检查显示端口被其他进程占用

处理顺序：

1. 如果是旧的 Docker 服务占用，先运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-stop.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-start.ps1
```

2. 如果是开发服务占用，例如本地前端或后端仍在运行，先关闭对应 PowerShell 窗口。
3. 如果需要同时保留 Docker 教师模式和开发调试，请让开发脚本使用隔离端口：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local-backend.ps1 -Port 8001
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local-frontend.ps1 -BackendPort 8001
```

不要把教师模式改到随机端口，否则老师手册、浏览器书签和通知链接会不一致。

## 四、后端未响应

典型提示：

- `Backend /health` 失败
- `Backend port 8000 no listener`
- 前端能打开，但页面一直加载或接口报错

处理顺序：

1. 先确认 Docker 本身已通过健康检查；如果 Docker daemon 不通过，先处理 Docker。
2. 查看后端容器是否运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-status.ps1
```

3. 如果 `backend` 容器不存在或不是 `running`，重新启动：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-start.ps1
```

4. 如果容器运行但 `/health` 仍失败，维护者查看日志：

```powershell
docker compose logs --tail 200 backend
```

优先检查数据库连接、环境变量、迁移版本和启动异常。不要直接删除数据库卷。

## 五、Worker 未响应

典型提示：

- `Celery worker ping` 失败
- 报告长时间停在 AI 处理中
- 定时抓取、通知摘要或 AI 生成没有继续推进

处理顺序：

1. 先确认 Redis、backend、celery-worker 容器都在运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-status.ps1
```

2. 重新运行健康检查，确认是否只是启动过程中的短暂未就绪：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-health.ps1
```

3. 如果 worker 仍失败，维护者查看日志：

```powershell
docker compose logs --tail 200 celery-worker
docker compose logs --tail 200 redis
```

4. 如果队列积压或任务卡住，先记录当前状态，再决定是否重启 worker。不要直接清空 Redis 队列，避免丢失正在处理的报告任务。

## 六、需要发给维护者的信息

出现无法自行处理的问题时，请记录：

1. 运行健康检查的时间。
2. 健康检查中第一个 `[FAIL]` 项。
3. 是否刚刚更新、重启或电脑休眠。
4. 页面地址和页面错误截图。
5. 如维护者要求，导出诊断包：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-diagnostics.ps1
```

诊断包位于 `local-diagnostics/`，默认不包含 `.env` 密钥文件。
