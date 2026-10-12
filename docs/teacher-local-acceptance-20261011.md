# 教师端脚本与文档总体验收记录

日期：2026-10-11

本文记录本轮教师端本地运行脚本、故障提示和配套文档的验收结果。当前机器 Docker Desktop 可执行 `docker --version` 和 `docker compose version`，但访问 `npipe:////./pipe/dockerDesktopLinuxEngine` 时返回 `permission denied`，因此本轮重点验收 Docker 权限失败路径；Docker 正常运行后的真实启停、备份和恢复流程仍需补测。

## 一、新增文件

- `scripts/teacher-local-docker.ps1`
  - 教师端 Docker 预检和错误提示共享 helper。
  - 统一识别 Docker CLI 缺失、Docker Desktop 未启动、Docker pipe 权限不足和其他 Docker 错误。
- `docs/teacher-local-startup-checklist.md`
  - 老师本地启动验收与故障分流清单。
  - 覆盖 Docker、端口、后端、worker 四类常见问题。
- `docs/teacher-local-acceptance-20261011.md`
  - 本轮总体验收记录。

## 二、修改文件

- `scripts/teacher-local-start.ps1`
  - 启动前先检查 Docker 是否可用。
  - Docker 不可用时直接给出处理建议并退出，不再输出 PowerShell 堆栈。
  - 保留端口 `3000` / `8000` 预检。
- `scripts/teacher-local-status.ps1`
  - 状态查询前先检查 Docker。
  - Docker 权限失败时输出可读建议。
- `scripts/teacher-local-health.ps1`
  - 增加 Docker daemon 检查。
  - Docker 不可用时容器项显示 `[SKIP]`，并提前停止，不再继续等待后端/前端 HTTP。
  - Docker pipe 权限失败时给出 `docker-users` 处理建议。
- `scripts/teacher-local-diagnostics.ps1`
  - 诊断包中的 Docker 命令输出改为结构化诊断文本，不再写入 PowerShell 堆栈。
  - 诊断包继续默认不包含 `.env`。
- `scripts/teacher-local-stop.ps1`
  - 停止服务前先检查 Docker。
- `scripts/teacher-local-backup.ps1`
  - 备份前先检查 Docker，再创建备份目录，避免失败时留下空目录。
- `scripts/teacher-local-update.ps1`
  - 更新流程入口先检查 Docker，失败时不会进入停止服务、迁移或重建步骤。
- `scripts/teacher-local-restore.ps1`
  - 备份目录不存在、缺少 `postgres-thinktank-monitor.sql` 时友好退出。
  - Docker 不可用时停止在 `RESTORE` 确认输入之前。
- `README.md`
  - 增加教师端启动验收清单入口。
- `docs/teacher-local-user-guide.md`
  - 增加 `-NoProfile` 命令口径和 Docker pipe 权限失败说明。
- `docs/deployment-maintenance.md`
  - 增加教师端启动验收清单入口。

## 三、已验证命令

以下命令已在当前 Docker pipe 权限失败环境下实测：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-health.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-status.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-start.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-diagnostics.ps1 -OutputRoot local-diagnostics-test -LogTail 20
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-stop.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-backup.ps1 -OutputRoot local-backups-test -SkipMinio
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-update.ps1 -SkipBackup -SkipPull -SkipMigrate -SkipHealthCheck
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-restore.ps1 -BackupDir local-backups-test\missing
```

另外构造了两个恢复脚本预检场景：

1. 备份目录存在但缺少 `postgres-thinktank-monitor.sql`。
2. 备份目录与 SQL 文件存在，但 Docker pipe 权限失败。

验收结论：

- 上述失败路径均无 PowerShell 异常堆栈。
- Docker 权限失败时提示一致，能说明 Docker Desktop、PowerShell 重开、`docker-users` 权限和重新登录。
- `health` 不再把 Docker 未就绪导致的容器检查误报为多个服务失败。
- `backup` 在 Docker 预检失败时不会创建空备份目录。
- `restore` 在 Docker 预检失败前不会进入 `RESTORE` 确认输入。
- 验收临时目录 `local-diagnostics-test`、`local-backups-test`、`local-restore-test` 已清理。

## 四、静态检查

已执行：

```powershell
git diff --check -- scripts/teacher-local-docker.ps1 scripts/teacher-local-health.ps1 scripts/teacher-local-start.ps1 scripts/teacher-local-status.ps1 scripts/teacher-local-diagnostics.ps1
git diff --check -- scripts/teacher-local-docker.ps1 scripts/teacher-local-stop.ps1 scripts/teacher-local-backup.ps1 scripts/teacher-local-update.ps1
git diff --check -- scripts/teacher-local-restore.ps1 scripts/teacher-local-docker.ps1
```

结果：

- 无空白错误。
- 仅有既有 LF/CRLF 换行提示。

已执行 PowerShell 语法解析：

- 当前 PowerShell 解析通过。
- Windows PowerShell 解析通过。
- 教师端脚本保持 ASCII 输出，避免 Windows PowerShell 5.1 读取无 BOM 脚本时出现中文编码解析问题。

## 五、仍需 Docker 正常环境补测

待 Docker Desktop 权限恢复后，在老师本地模式下补测：

1. `teacher-local-start.ps1`
   - Docker 正常且端口空闲时能启动全部服务。
   - Docker 服务已占用 `3000` / `8000` 时不会误报端口冲突。
   - 非 Docker 进程占用 `3000` / `8000` 时能明确提示。
2. `teacher-local-health.ps1`
   - 所有服务运行时健康检查通过。
   - 后端容器未就绪时能等待并给出合理失败信息。
   - worker 未响应时只标记 worker 问题，不误判 Docker 或前端。
3. `teacher-local-diagnostics.ps1`
   - Docker 正常时诊断包包含 compose 状态和各服务日志。
   - 诊断包仍不包含 `.env`。
4. `teacher-local-backup.ps1`
   - PostgreSQL 备份文件非空。
   - `-SkipMinio` 和默认 MinIO 备份路径均符合预期。
5. `teacher-local-restore.ps1`
   - 用受控测试备份验证 `RESTORE` 二次确认。
   - 恢复前安全备份、数据库恢复、MinIO 跳过/恢复、健康检查顺序正确。
   - 不使用真实老师数据库做破坏性恢复测试。
6. `teacher-local-update.ps1`
   - 有维护窗口和备份后再测完整流程。
   - 重点确认队列检查、迁移、外发关闭检查和启动新版进程顺序。

## 六、提交前注意

本轮涉及未跟踪文件：

- `scripts/teacher-local-docker.ps1`
- `docs/teacher-local-startup-checklist.md`
- `docs/teacher-local-acceptance-20261011.md`

提交时需要一并加入。当前工作区仍有大量早前改动，提交前应按主题拆分或至少复核 `git status --short`。
