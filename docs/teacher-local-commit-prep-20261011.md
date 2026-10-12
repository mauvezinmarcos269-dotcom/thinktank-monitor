# 教师端脚本与文档提交准备清单

日期：2026-10-11

本文只准备“教师端本地脚本与文档”这一组的提交候选，不实际执行 `git add` 或 `git commit`。当前工作区存在 staged 与 unstaged 混合状态，正式提交前建议先按本文重新整理暂存区。

## 一、当前相关状态

相关文件当前状态：

```text
M  .gitignore
MM README.md
MM docs/deployment-maintenance.md
MM docs/teacher-local-user-guide.md
 M scripts/teacher-local-backup.ps1
AM scripts/teacher-local-diagnostics.ps1
 M scripts/teacher-local-health.ps1
 M scripts/teacher-local-restore.ps1
 M scripts/teacher-local-start.ps1
 M scripts/teacher-local-status.ps1
 M scripts/teacher-local-stop.ps1
 M scripts/teacher-local-update.ps1
?? docs/teacher-local-acceptance-20261011.md
?? docs/teacher-local-startup-checklist.md
?? scripts/teacher-local-docker.ps1
```

说明：

- `MM` 表示同一文件既有已暂存内容，也有未暂存新修改。
- `AM` 表示文件已作为新增暂存过，但工作区还有后续修改。
- `.gitignore` 的 `local-diagnostics/` 忽略规则属于教师端诊断包范围，建议纳入本组。

## 二、先取消旧暂存

如果决定按主题重新提交，先取消本组相关文件的旧暂存：

```powershell
git restore --staged .gitignore README.md docs/deployment-maintenance.md docs/teacher-local-user-guide.md scripts/teacher-local-diagnostics.ps1
```

这一步只影响暂存区，不会丢失工作区改动。不要使用 `git reset --hard`。

取消暂存后复查：

```powershell
git status --short -- .gitignore README.md docs/deployment-maintenance.md docs/teacher-local-user-guide.md docs/teacher-local-startup-checklist.md docs/teacher-local-acceptance-20261011.md scripts/teacher-local-*.ps1
```

## 三、建议直接加入的文件

这些文件基本都属于教师端本地脚本与文档组，可直接加入：

```powershell
git add .gitignore
git add scripts/teacher-local-docker.ps1
git add scripts/teacher-local-start.ps1
git add scripts/teacher-local-status.ps1
git add scripts/teacher-local-health.ps1
git add scripts/teacher-local-diagnostics.ps1
git add scripts/teacher-local-stop.ps1
git add scripts/teacher-local-backup.ps1
git add scripts/teacher-local-update.ps1
git add scripts/teacher-local-restore.ps1
git add docs/teacher-local-startup-checklist.md
git add docs/teacher-local-acceptance-20261011.md
```

## 四、建议交互加入的文件

这些文件有交叉改动，建议用 `git add -p`，只选择教师端相关 hunk：

```powershell
git add -p README.md
git add -p docs/deployment-maintenance.md
git add -p docs/teacher-local-user-guide.md
```

建议纳入的内容：

- README 中的教师端使用说明、启动验收清单链接、教师端脚本列表。
- `docs/deployment-maintenance.md` 中的教师手册、启动验收清单、总体验收记录链接，以及教师端健康检查失败分流说明。
- `docs/teacher-local-user-guide.md` 中的 `-NoProfile` 命令、启动验收清单链接、Docker pipe 权限失败说明。

建议暂不纳入的内容：

- 与纯开发端口配置有关、但不属于教师端脚本组的改动。
- 与通知 payload、LLM 授权、采集解析、前端报告页 UI 相关的改动。

如果 `git add -p` 很难拆分 README 或部署文档，可接受把这三个文档整体放入教师端组，但提交说明里要注明也包含本地命令口径文档更新。

## 五、暂存后复核命令

暂存后运行：

```powershell
git diff --cached --name-status
git diff --cached --check
```

建议检查暂存文件应主要包含：

```text
.gitignore
README.md
docs/deployment-maintenance.md
docs/teacher-local-user-guide.md
docs/teacher-local-startup-checklist.md
docs/teacher-local-acceptance-20261011.md
scripts/teacher-local-docker.ps1
scripts/teacher-local-start.ps1
scripts/teacher-local-status.ps1
scripts/teacher-local-health.ps1
scripts/teacher-local-diagnostics.ps1
scripts/teacher-local-stop.ps1
scripts/teacher-local-backup.ps1
scripts/teacher-local-update.ps1
scripts/teacher-local-restore.ps1
```

`docs/precommit-grouping-audit-20261011.md` 和本文可以单独作为“提交准备文档”提交，也可以和教师端组一起提交；如果追求业务提交更干净，建议单独提交审计文档。

## 六、提交前验证

当前 Docker Desktop 权限失败环境下，至少验证失败路径：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-health.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-status.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-start.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-stop.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-backup.ps1 -OutputRoot local-backups-test -SkipMinio
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-update.ps1 -SkipBackup -SkipPull -SkipMigrate -SkipHealthCheck
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-restore.ps1 -BackupDir local-backups-test\missing
```

语法检查：

```powershell
$files = @(
  'scripts/teacher-local-docker.ps1',
  'scripts/teacher-local-start.ps1',
  'scripts/teacher-local-status.ps1',
  'scripts/teacher-local-health.ps1',
  'scripts/teacher-local-diagnostics.ps1',
  'scripts/teacher-local-stop.ps1',
  'scripts/teacher-local-backup.ps1',
  'scripts/teacher-local-update.ps1',
  'scripts/teacher-local-restore.ps1'
)
foreach ($file in $files) {
  $errors = $null
  [System.Management.Automation.PSParser]::Tokenize((Get-Content -LiteralPath $file -Raw), [ref]$errors) | Out-Null
  if ($errors.Count -gt 0) {
    Write-Host "SYNTAX FAIL $file"
    $errors | Format-List
    exit 1
  }
}
```

验证后确认没有测试产物：

```powershell
Test-Path local-diagnostics-test
Test-Path local-backups-test
Test-Path local-restore-test
```

三项都应为 `False`。

## 七、建议提交信息

```text
Improve teacher local Docker diagnostics and startup docs
```

建议提交说明正文：

```text
- add shared teacher-local Docker readiness helper
- improve health/start/status/diagnostics failure messages for Docker Desktop permission issues
- guard backup/update/restore before destructive or noisy flows
- add teacher startup checklist and acceptance record
```

## 八、暂不提交的其他组

本组之外，暂不纳入：

- 通知 payload 与每日摘要来源链接。
- LLM 授权边界与默认不外发。
- 采集调度、锁、错误摘要与候选跳过原因。
- PDF/文档发现与解析器修复。
- 前端报告页、设置页和轮询 UI 整理。
- AI 字段、报告服务与 worker 管线。
