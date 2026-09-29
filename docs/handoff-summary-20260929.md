# 阶段性交付说明

更新时间：2026-09-29

本文汇总本轮围绕“全球智库涉华研究实时监测、翻译、分析和提醒平台”的阶段性整理结果，便于向老师说明当前系统状态、使用方式和下一步开发重点。

## 一、当前结论

平台已经具备较完整的本地运行闭环：

1. 监测重点智库来源。
2. 发现候选报告并做文档门槛检查。
3. 保存符合条件的涉华报告。
4. 生成全文翻译稿、主要观点和深层研判。
5. 前端人工复核。
6. 导出 Word / Markdown 成果。
7. 通过站内通知和每日摘要提醒用户。

本轮重点不是盲目增加来源，而是把页面、来源策略、AI 质量约束和本地部署维护流程收敛到更清晰、可解释、可长期运行的状态。

## 二、本轮完成事项

### 1. 页面清晰化

- 仪表盘改为“今日工作台”结构。
- 突出待复核与交付、未读提醒、AI 异常、来源需处理。
- 顶部导航的未读通知改为角标显示。

### 2. 报告工作台优化

- 成果区改为“交付材料”口径。
- 阅读顺序调整为：主要观点、深层研判、全文翻译、原文正文。
- 底部操作区区分“管理员维护”和“补充复制与导出”。

### 3. 来源稳定化

- 修正小批量入库脚本默认来源，移除已被标记为 `blocked` 的 Heritage。
- 默认试运行来源改为 Brookings、CFR、PIIE。
- 增加测试，避免默认 keys 误包含 blocked 来源。
- 同步修正文档中过期的 Heritage / AEI 准入口径。

### 4. AI 成果质量闭环

- 主要观点和深层研判不仅校验字数，也校验中文编号分论点数量。
- 主要观点要求至少 4 个中文编号分论点。
- 深层研判要求至少 4 个中文编号分论点，建议写到 5 个。
- 补充测试，保证无编号但字数足够的内容也会触发重试。

### 5. 老师本地电脑部署与维护

- 补齐 `.env.example` 中通知、LLM 超时和 AI 分块配置。
- 新增部署维护手册。
- 新增老师本地使用指南。
- 新增本地启动、停止、状态检查 PowerShell 脚本。

## 三、老师本地运行方式

启动：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/teacher-local-start.ps1
```

首次部署或更新后重建：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/teacher-local-start.ps1 -Build
```

查看状态：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/teacher-local-status.ps1
```

停止：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/teacher-local-stop.ps1
```

浏览器访问：

```text
http://localhost:3000
```

## 四、当前稳定来源口径

可小批量试运行：

- Brookings
- CFR
- CSIS
- PIIE
- AEI
- ECFR

继续阻塞，不自动入库：

- CAP
- Cato
- Heritage

其他来源进入自动入库前，必须先完成只读审计、小样本复核和人工确认。

## 五、验证结果

本轮最终检查结果：

| 检查项 | 结果 |
| --- | --- |
| 后端 `poetry run pytest` | 180 passed |
| 后端 `poetry run ruff check .` | 通过 |
| 前端 `npm run typecheck` | 通过 |
| 前端 `npm run lint` | 通过 |

## 六、建议下一步

1. 在老师电脑上按本地部署手册完成 Docker Desktop 部署。
2. 配置真实 `.env` 和 `backend/.env`，尤其是数据库密码、JWT 密钥、LLM Key。
3. 创建管理员账号。
4. 先只运行已验证来源，观察 1-2 周。
5. 每周向老师汇总新增报告、复核通过率、AI 失败原因和来源健康。
6. 老师确认质量后，再扩展 RAND、Carnegie、Chatham House、Bruegel、JIIA 等来源的只读审计。
