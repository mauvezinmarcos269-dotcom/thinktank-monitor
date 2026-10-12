# LLM 授权功能隔离部署验收

日期：2026-10-05。范围：外发保持关闭时的 PostgreSQL 迁移、API、Worker、Beat 运行验收及正式切换准备。

## 验收结果

| 检查 | 结果 |
| --- | --- |
| 空 PostgreSQL 迁移至旧版本 `b23c7a91e8d4` | 通过。修复了历史迁移 `e038b9014347` 缺失的 `translation`、`summary`、`commentary`、`ai_status`、`ai_generated_at` 字段。 |
| 旧版历史记录升级至 `c8e4a6d91203` | 报告和候选各 1 条保留；授权记录 0 条，旧候选新字段为 `NULL`。 |
| 回滚至 `b23c7a91e8d4` 并再次升级 | 历史记录保留；回滚后授权表和候选新字段消失；再次升级后授权仍为 0 条。 |
| 隔离 API | `127.0.0.1:8012/health` 返回 `ok`，OpenAPI 存在授权预览、列表/批准及撤销路径。 |
| 隔离 Worker | 独立 Redis DB 15、独立队列；调度任务返回 `[]`，直接分块任务返回 `blocked`。分块和报告状态仍为 `pending`，重试次数均为 0。 |
| 涉华抽样 | 返回 `LLMNotAuthorized`，原因为外发总开关关闭。 |
| 隔离 Beat | 2026-10-05 00:00 投递采集与 AI 调度任务；采集返回 `selected_count=0`，AI 调度返回 `[]`。 |
| 清理 | 临时 API/Worker/Beat 进程已终止，端口 8012 已关闭；测试数据库已删除，Redis DB 15 已清空。 |

隔离进程的 `LLM_OUTBOUND_ENABLED=false`，LLM 目标为不可用的本机测试地址，未写入真实授权。Worker 日志没有模型 HTTP 调用记录。该结果证明本次隔离配置下任务被阻断；不等于旧版正式 Worker 已加载新代码。

回归检查：后端 `351 passed`，Ruff 通过；前端 TypeScript、ESLint 和生产构建通过；PowerShell 更新脚本语法及 Compose 配置校验通过。测试的 411 条弃用警告来自既有 `datetime.utcnow()` 默认值。

## 正式环境切换顺序

1. 明确维护窗口，确认使用的是已审阅的同一代码版本；核对实际 `.env` 中 `LLM_OUTBOUND_ENABLED=false`。识别 Compose 之外的本地 Worker、Beat 和手动脚本，安排它们停止投递。
2. 完成 PostgreSQL、MinIO 和配置备份，并验证备份文件可读、非空；记录正式库当前 Alembic 版本、容器状态及队列长度。当前只读快照中的正式库版本为 `b23c7a91e8d4`，执行当天需重新核对。
3. 停止旧 Beat 和 API，让旧 Worker 完成正在执行的任务后停止。检查 Redis 默认队列和 `unacked`；有任务残留则先人工复核，不清空队列。
4. 构建同一版本的后端、Worker、Beat、前端镜像。通过一次性后端容器执行 `alembic upgrade head`，随后执行 `alembic current --check-heads`；迁移失败时保持应用进程停止并排查。
5. 在一次性后端容器中核对外发总开关仍为关闭，然后启动新版 API、Worker、Beat 和前端。确认它们均为切换后启动的新进程，检查健康端点、Worker ping、授权接口、定时投递、数据库授权表记录数和错误日志。
6. 观察至少一次五分钟调度周期；核对到期来源的实际抓取结果，以及未授权报告未进入 AI 队列。授权记录应仍为 0，除非后来另有逐篇批准。

已修正 `scripts/teacher-local-update.ps1` 的默认顺序，覆盖第 2 至第 5 项，并在 `-SkipMigrate` 时仍校验数据库版本。脚本尚未对正式环境执行；正式切换需要单独确认维护窗口、备份与实际队列状态。现有普通 `teacher-local-start.ps1 -Build` 会直接启动服务，不应用它替代本次受控更新。

当前本机代码仍有未提交改动。审阅并固定代码版本后，如使用当前目录代码，受控更新入口为 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/teacher-local-update.ps1 -SkipPull`；默认形式会先执行 `git pull --ff-only`。脚本不会删除队列中的任务，遇到未处理任务会停止并要求人工复核。

如果迁移后健康检查失败，保持 Beat 和 Worker 停止，先查原因。不要直接对正式库执行 `alembic downgrade`：该操作会删除授权审计表；如需恢复，按已验证的备份恢复方案另行决定。

本次没有修改正式数据库、实际环境变量、来源配置或授权记录，也没有重启正式 API、Worker、Beat。启用外发和批准真实文档属于后续独立决策。

当前 Compose 后端挂载源码并使用 `uvicorn --reload`，文件变化可能使 API 在数据库迁移前先加载新代码；Worker 和 Beat 则不会自动重新加载。正式切换完成前，不能以页面可打开或容器处于 `running` 状态代替版本一致性验收。

## 正式环境执行结果

2026-10-05 21:00 至 21:05 已按上述顺序完成正式切换：

- 切换前正式库版本为 `b23c7a91e8d4`，报告 420 条、候选 2614 条；默认队列、`unacked`、Worker 活动任务和预留任务均为 0，外发总开关为关闭。
- 备份保存于 `local-backups/20261005-210027/`。PostgreSQL 导出为 22,090,541 字节，MinIO 备份含 18 个文件、23,477 字节，并保存根目录和后端两份环境配置。
- 旧 Beat、API、Worker 已停止；后端、Worker、Beat、前端镜像已使用当前验收代码重建。正式库已升级至 `c8e4a6d91203` 并通过 `alembic current --check-heads`。
- 新版服务启动后，正式库仍有报告 420 条、候选 2614 条，授权记录 0 条；`LLM_OUTBOUND_ENABLED=false`。API OpenAPI 已出现 3 个授权路径，Worker 已注册新的分块与授权保护任务。
- 初次健康检查在容器启动约 1 秒时访问后端，连接被关闭；数秒后后端健康检查返回 200，日志显示应用正常启动。`teacher-local-health.ps1` 已增加最多 15 次、间隔 2 秒的就绪重试，修正后整套健康检查通过。
- 21:05 首个正式五分钟周期中，Beat 投递 `crawl.all_sources` 和 `report.enqueue_ai_chunk_tasks`。采集结果为 `selected_count=0`，AI 调度返回 `[]`；队列和 `unacked` 均为 0，授权仍为 0，没有模型外发。

正式部署已完成“默认不外发”的版本切换。后续如需进行涉华抽样或全文生成，仍须先单独开启总开关，再按用途和文档版本逐项授权；本次执行没有进行这两项操作。

## 正式页面只读走查

在外发关闭、授权记录为 0 的正式环境中，以管理员会话完成报告 447 的授权页面走查：

- 桌面端 1440×1000 正确展示报告标题、141,021 字符、发送范围、服务类型、端点、模型、文档哈希和“外发总开关已关闭”。授权历史为 0。
- 明确同意复选框初始未选中，“确认授权”按钮初始禁用；勾选后按钮启用，但未点击提交，随后取消勾选并关闭对话框。
- 移动端 390×844 的对话框边界为 352×812，完整位于视口内且可滚动，长端点和文档哈希正常换行，按钮状态与桌面端一致。
- 两次页面走查的授权接口请求均只有 GET，浏览器控制台和页面无错误；走查前后授权记录均为 0。
- 正式库暂无 `pending_relevance` 候选。历史候选 2671 缺少迁移前未保存的文档版本，抽样预览按设计返回 409“候选尚无有效文档版本，请先完成文档提取”，没有凭 URL 或历史报告反推授权版本。

证据截图保存在 `.codex-backups/llm-authorization-deployment-acceptance-20261004/formal-report-447-authorization-preview.png` 和 `formal-report-447-mobile-preview.png`。本轮没有批准、撤销、采集或 AI 请求。
## 后续候选监测

- 正式库当前没有 `pending_relevance` 候选，LLM 外发继续保持关闭。
- 2026-10-05 20:35–20:43（北京时间）的 `crawl_run_id=749–759` 发生在正式数据库迁移前：Worker 已加载包含 `document_hash` 字段的新代码，而数据库仍为旧结构，因此均因缺少 `crawl_candidates.document_hash` 失败，未保存候选。
- 上述失败运行仍更新了来源的 `last_crawled_at`；当前准入来源的下一次自然到期时间集中在 2026-10-06 20:39–20:43（北京时间）。迁移完成后的 21:05 调度周期未选中来源，符合尚未到期的状态。
- 后续保持静默监测。首次出现真实 `pending_relevance` 候选后，只进行涉华抽样授权页面的只读预览验收，不批准、不撤销、不触发 AI，并再次核对外发开关、授权记录、队列和日志。
- 未经另行确认，不手动修改 `last_crawled_at`，不主动触发采集任务。

## 首批真实待抽样候选验收（2026-10-06）

- 2026-10-06 20:40–20:47（北京时间），准入来源自然产生 `crawl_run_id=760–770`；11 次运行均为 `success`。正式库首次出现 21 条 `pending_relevance` 候选。
- 抽取三条标题明确涉华的 RAND 候选进行桌面页面走查：`2825`（run 767）、`2826`（run 767）和 `2839`（run 769）。三条候选均为 74–76 页 PDF，具有非空 `document_hash` 和正文长度。
- 三个“涉华抽样授权”弹窗均正常显示文档、字符数、发送范围、服务类型、端点、模型、文档版本和外发总开关。页面显示“未授权”“已关闭”，同意框保持未勾选，“确认授权”按钮保持禁用，授权历史为 0。
- 浏览器层为授权接口设置了只读保护。实际请求仅为每个候选各一次预览 `GET` 和授权历史 `GET`，没有 `POST`、`DELETE`、`PUT` 或 `PATCH`；保护层没有拦截到写请求。
- 走查后数据库仍为：`LLM_OUTBOUND_ENABLED=false`、授权记录 0、`pending_relevance` 21；三条抽样候选状态未变，`is_china_related` 仍为 `NULL`。Celery 队列和 `unacked` 均为 0。
- 从自然采集窗口开始审计 Worker、Beat 和 Backend 日志：没有模型 HTTP 调用，没有授权写请求；无 PDF 和不足 20 页的候选按既有规则跳过，调度批次本身均成功。
- 结构化证据保存在 `.codex-backups/llm-authorization-deployment-acceptance-20261004/pending-relevance-preview-walkthrough-20261006.json`；截图为同目录下的 `pending-relevance-2825-authorization-preview.png`、`pending-relevance-2826-authorization-preview.png` 和 `pending-relevance-2839-authorization-preview.png`。

## 跨来源待授权候选去重（2026-10-06）

- 首批 21 条待授权候选中，`2825/2839` 与 `2826/2836` 分别指向相同 RAND 报告页和 PDF，但来自网站源 `7` 与出版物源 `56`，暴露出候选去重此前只覆盖同一来源和已入库报告的问题。
- 新逻辑在文档提取前按全库规范化报告 URL 检查，在文档提取后按最终 PDF URL 再检查；已入库报告继续使用 `duplicate_existing`，既有 `pending_relevance` 使用新增原因 `duplicate_pending`（“已有待授权候选”）。历史失败、非涉华或文档失败候选不会阻断后续重试。
- 自动采集服务与 `pilot_crawl_sources` 共用同一去重实现。正式库只读演练中，候选 `2825`、`2826`、`2836`、`2839` 均被识别为 `pending_candidate`，未更新任何记录。
- 针对性测试 66 项通过；完整后端测试 355 项通过，Ruff 通过。正式库现有两组重复候选仍未处理。

## 跨来源去重 Worker 切换验收（2026-10-06）

- 23:02（北京时间）切换前，Worker 活动任务、预留任务和 Redis 默认队列均为 0，`LLM_OUTBOUND_ENABLED=false`；因此仅重启 `celery-worker`，未重启 Beat、API 或其他服务。
- 新 Worker 于 23:03 就绪并通过 Celery ping；容器内已加载 `CandidateDuplicateIndex` 和 `duplicate_pending`，外发总开关仍为关闭，任务注册列表完整，启动日志无异常。
- 23:05 自然调度周期中，Beat 准时投递 `crawl.all_sources` 和 `report.enqueue_ai_chunk_tasks`。采集任务返回 `selected_count=0`，AI 调度返回 `[]`，两项任务均成功结束。
- 周期完成后，Redis 默认队列为 0，未发现 `unacked` 键；正式库仍有 21 条 `pending_relevance` 候选，授权记录总数和有效授权数均为 0。本次重启与验收未修改现有重复候选，也未产生模型外发。

## 历史重复候选修正（2026-10-06）

- 经人工确认后，对两组 RAND 跨来源重复候选执行受约束事务：保留较早的 `2825`、`2826` 为 `pending_relevance`，将较晚的 `2839`、`2836` 标记为 `skipped / duplicate_pending`（“已有待授权候选”）。
- 事务提交前要求四条候选均保持 `pending_relevance` 且报告 URL 与预期完全一致，并要求实际更新数恰为 2；任一条件不满足都会整体回滚。
- 四条候选的修改前完整数据库行备份在 `.codex-backups/20261006-cross-source-dedupe/crawl-candidates-2825-2826-2836-2839-before-history-dedupe.json`，备份已通过 JSON 解析和 ID 完整性检查。
- 修正后候选总量保持 2,800 条，`pending_relevance` 从 21 条降至 19 条，`duplicate_pending` 为 2 条；授权记录仍为 0，`LLM_OUTBOUND_ENABLED=false`，Celery 默认队列为 0。本次操作没有触发采集、授权或模型外发。

## 历史重复候选页面走查（2026-10-06）

- 使用隔离的无界面 Edge 和 15 分钟本地管理员会话完成正式本地页面只读走查，未安装新依赖。浏览器会话及调试端口在验收后均已关闭。
- 仪表盘“候选报告质量”显示候选总数 2,800、待授权 19、已跳过 2,646；主要跳过原因新增“已有待授权候选 2”，与数据库统计一致。
- 在系统设置中搜索 RAND，展开出版物源 `56` 的 `crawl_run_id=769`。该运行页面显示全部 20、待授权 14、已跳过 6，“已有待授权候选 2”。
- 选择“已跳过 / 已有待授权候选”后，页面显示 2 条：`Assessing Chinese and U.S. Technology Diffusion Capacity`（76 页）和 `The Emerging Digital Battleground`（74 页）。同一只读列表接口返回候选 ID `2839`、`2836`，状态和原因均正确。
- 两轮浏览器走查均没有非 GET 请求、控制台错误或页面异常。走查后授权记录仍为 0，`LLM_OUTBOUND_ENABLED=false`，`pending_relevance=19`，`duplicate_pending=2`，Celery 默认队列为 0。
- 结构化证据和截图保存在 `.codex-backups/20261006-cross-source-dedupe/ui-walkthrough-after-history-dedupe.json`、`dashboard-candidate-quality-after-history-dedupe.png` 和 `rand-run-769-duplicate-pending-filter.png`。
- 走查同时发现可读性问题：历史失败运行会在“质量/错误摘要”中直接展示很长的 SQL 异常和参数内容，挤占候选表格下方空间。该问题未影响本次筛选结果，本轮未修改展示逻辑。

## 抓取错误摘要与详情优化（2026-10-07）

- “质量/错误摘要”默认显示最多 180 个字符；SQLAlchemy 异常会在 `[SQL:` 或 `[parameters:` 之前截断，避免 SQL 语句和参数默认铺满表格。完整原文仍保留在原生“展开详情/收起详情”控件中。
- 展开后的详情区最高为 14rem（实际 224px），超长内容在区域内部滚动；正常质量指标和跳过原因徽章继续显示，较长的质量记录同样可以按需展开。
- TypeScript、ESLint、Prettier 和 Next.js 生产构建均通过。正式本地环境仅重建并替换了 `frontend` 容器，后端、Worker、Beat 和数据库没有重启或迁移。
- 实际页面走查验证：默认摘要为 180 字符且不含 SQL/parameters；展开后两类内容均可见，控件文案正确切换；移动端 390×844 下摘要宽约 291px，页面无横向溢出。
- 两轮页面交互没有非 GET 请求、控制台错误或页面异常。走查后仍为 `pending_relevance=19`、`duplicate_pending=2`、授权记录 0、`LLM_OUTBOUND_ENABLED=false`、Celery 默认队列 0。
- 证据保存在 `.codex-backups/20261007-crawl-error-disclosure/error-disclosure-walkthrough.json`、`error-summary-desktop.png`、`error-details-expanded-desktop.png` 和 `error-summary-mobile.png`。

## 教师友好的中文错误摘要（2026-10-07）

- 基于正式数据库备份中的真实历史错误，新增数据库字段未同步、HTTP 状态异常、全部发现入口失败、连接失败、访问超时、RSS 解析失败和未配置专用解析器等中文摘要规则。未知异常继续回退到安全截断后的原始摘要，不做无依据归类。
- `ProgrammingError / UndefinedColumnError` 的实际页面摘要由英文技术栈改为“数据库结构未同步：数据表 crawl_candidates 缺少字段 document_hash。”；完整英文异常、SQL 和参数仍保留在“展开详情”中。
- 六类真实样本通过直接加载当前 TypeScript 源文件的断言；TypeScript、ESLint、Prettier、Next.js 生产构建和 `git diff --check` 均通过，未引入新依赖。
- Docker Desktop 曾处于停止状态，恢复后所有 Compose 容器依照重启策略自动启动；随后仅重建 `frontend` 容器部署本次页面修改。外发总开关重新核验为关闭。
- 桌面和 390×844 移动页面走查均通过：中文摘要默认可见且不包含 SQL/parameters，展开后原文完整、详情区内部滚动，移动页面无横向溢出；没有非 GET 请求、控制台错误或页面异常。
- 19:00 和 19:05 自然调度周期中，采集均无到期来源，AI 调度均返回空列表；19:00 按计划生成 1 条每日摘要通知。走查后仍为 `pending_relevance=19`、`duplicate_pending=2`、授权记录 0、Celery 默认队列 0。
- 证据保存在 `.codex-backups/20261007-chinese-error-summary/verify-error-summaries.cjs`、`chinese-error-walkthrough.json`、`chinese-error-summary-desktop.png`、`chinese-error-details-expanded-desktop.png` 和 `chinese-error-summary-mobile.png`。

## 仪表盘与每日汇总统一错误摘要（2026-10-07）

- 后端新增共享抓取错误摘要服务，仪表盘“最近失败原因”和后续生成的每日汇总通知使用同一组中文规则。未知错误仍保留最多 180 个字符的回退摘要，不改变数据库中的原始抓取错误。
- 前端把设置页规则提取为共享工具；历史每日汇总在展示时逐条转换失败原因，并隐藏旧 SQLAlchemy 异常中的 SQL、参数和其他技术续行。数据库内的历史通知原文未修改，其他通知类型不参与转换。
- 通知正文保留原有换行，并允许超长 URL 换行。桌面实际走查显示最新每日汇总为 16 行；390×844 移动端页面宽度与视口同为 390px，无横向溢出。
- 后端摘要单元与通知集成测试共 11 项通过，完整后端测试 364 项通过，Ruff 通过；前端历史多行样本断言、TypeScript、ESLint、Prettier 和 Next.js 生产构建均通过，未引入新依赖。
- 正式本地页面只读走查验证：仪表盘 5 条失败原因均为中文摘要；每日汇总筛选返回的 25 条历史通知中，`ValueError`、`TimeoutError`、`HTTPStatusError`、`ProgrammingError` 和 `[SQL:` 的展示计数均为 0。
- 走查期间没有非 GET 请求、控制台错误或页面异常；未标记通知、未触发采集、未创建授权、未调用模型服务。仅重建了 `frontend` 容器，后端源码由既有热加载生效，Worker 已在此前空队列检查后加载新通知摘要代码。
- 结构化证据和截图保存在 `.codex-backups/20261007-shared-crawl-error-summary/dashboard-notification-walkthrough.json`、`dashboard-failure-summary-desktop.png`、`daily-summary-notification-desktop.png` 和 `daily-summary-notification-mobile.png`。

## 设置页来源卡片错误摘要（2026-10-07）

- 设置页来源卡片顶部的 `source.last_error` 已接入前端共享中文摘要，不再默认直接展示技术异常。活动来源显示“最近错误”，停用来源显示“停用前最近错误”。
- 完整原始错误仍通过原生“展开详情/收起详情”控件保留，默认收起；来源卡片内摘要使用完整可用宽度，抓取记录表格内既有 360px 限制不受影响。
- 使用活动的布鲁盖尔研究所来源验证未配置解析器摘要，使用停用的 RAND RSS 来源验证 HTTP 404 摘要。两项默认视图均不含 `ValueError` 或 `HTTPStatusError`，展开后原文完整可见。
- 390×844 移动端中，错误块宽 290px，文档宽度与视口同为 390px，无横向溢出，详情保持收起。
- Prettier、TypeScript、ESLint 和 Next.js 生产构建均通过；仅重建 `frontend` 容器，未引入依赖，未修改来源数据。
- 页面走查没有非 GET 请求、控制台错误或页面异常。结构化证据及截图保存在 `.codex-backups/20261007-source-card-error-summary/source-card-error-walkthrough.json`、`active-source-summary-desktop.png`、`active-source-details-desktop.png`、`disabled-source-summary-desktop.png` 和 `disabled-source-summary-mobile.png`。

## 报告处理失败通知可读化（2026-10-07）

- `report.ai_failed` 和 `report.fetch_failed` 的未来通知由后端生成“报告标题 + 失败原因”的教师可读文本。AI 摘要稿、评论稿和翻译稿的长度异常会保留要求字数与实际字数；网络、服务配置、授权、返回格式和空内容等错误分别提供中文摘要。
- 历史库共有 65 条 `report.ai_failed` 通知，全部属于最终摘要稿或评论稿长度校验失败；数据库原文未修改，前端展示层将其转换为可读格式。报告标题自带冒号时使用已知错误边界解析，不按第一个冒号截断。
- `report.review_needs_rerun` 保存的是老师复核意见，不属于技术异常，本轮明确保持原文和现有布局不变。当前库没有 `report.fetch_failed` 或 `report.review_needs_rerun` 历史通知。
- 后端新增 9 个报告处理错误摘要测试；完整后端测试 373 项通过，Ruff 通过。前端历史样本断言、Prettier、TypeScript、ESLint 和 Next.js 生产构建均通过，未引入新依赖。
- 部署前确认 Worker 活动任务、预留任务和 Redis 默认队列均为空；随后仅重启 `celery-worker` 并重建 `frontend`。Worker 容器已实际导入新摘要模块并返回预期文案，Celery ping 正常。
- 页面只读走查中，管理员可见的 65 条历史 AI 失败通知技术关键词计数为 0，可读原因计数为 65；Guardian Tiger III 的完整标题得到保留，通知正文为三行结构。
- 390×844 移动端文档宽度与视口同为 390px，无横向溢出；走查没有非 GET 请求、控制台错误或页面异常，也没有触发 AI、正文抓取、标记已读或通知写入。
- 结构化证据和截图保存在 `.codex-backups/20261007-report-notification-error-summary/report-notification-walkthrough.json`、`ai-failure-notifications-desktop.png` 和 `ai-failure-notifications-mobile.png`。

## 报告详情页错误摘要（2026-10-07）

- 报告详情页新增共用错误展示组件，报告级 `crawl_error`、AI 进度的 `latest_error` 和每条分块的 `last_error` 均默认显示教师可读摘要；摘要与原文不同时提供“展开详情/收起详情”。
- 原始技术错误保留在最高 12rem 的等宽详情区中，可独立滚动。失败分块原有类型、序号、状态、重试次数和顺序均保持不变。
- 正式库当前没有非空报告级 `crawl_error`，未为验收伪造或写入报告数据。AI 分块共有 13 条历史错误；选择 report 382（`Understanding China's Naval Maintenance Management`）进行真实页面走查，该报告有 3 条失败翻译分块。
- report 382 的最近错误显示“AI 返回格式异常：未获得有效的结构化内容。”；3 条分块分别显示 1 条格式异常和 2 条翻译稿长度不足摘要，要求字数与实际字数完整保留，技术关键词默认展示计数为 0。
- 最近错误和分块详情默认收起，展开后原始 `ValueError` 完整可见，控件文案正确切换。390×844 移动端错误块宽约 293px，页面无横向溢出，详情保持收起。
- Prettier、TypeScript、ESLint 和 Next.js 生产构建均通过；仅重建 `frontend` 容器，未重启后端、Worker 或 Beat，未引入新依赖。
- 页面走查没有非 GET 请求、控制台错误或页面异常，也没有触发抓取、AI 重跑、授权或复核写入。结构化证据和截图保存在 `.codex-backups/20261007-report-detail-error-summary/report-detail-error-walkthrough.json`、`report-382-errors-collapsed-desktop.png`、`report-382-errors-expanded-desktop.png` 和 `report-382-errors-mobile.png`。

## 候选说明错误摘要（2026-10-07）

- 设置页候选表不再直接铺开技术错误。正文检查和 AI 判断失败统一使用共享错误展示组件，默认显示中性中文摘要；摘要与原文不同时提供“展开详情/收起详情”。报告详情页既有错误展示同步复用该组件。
- 涉华判断理由保持完整原文。候选的 `error` 与 `relevance_reason` 相同时只展示一次，不将正常判断理由误标成技术错误；两者不同时分别保留技术摘要和判断理由。
- HTTP 摘要规则兼容带或不带 `HTTPStatusError:` 前缀的 httpx `Client error` / `Server error`。新增真实无前缀 403 样本测试；完整后端测试 374 项、Ruff、Prettier、TypeScript、ESLint 和 Next.js 生产构建均通过，未引入新依赖。
- 在隔离本地服务 `3001/8001` 上完成真实页面只读走查。Atlantic Council 批次 `771` 的候选 `2942` 默认显示“检查结果：报告正文地址请求失败：返回 HTTP 404。”，展开后完整原始错误可见；RAND 批次 `780` 的候选 `3022` 显示“AI 判断：AI 处理未执行：外发总开关已关闭。”。
- 设置页每个来源只暴露最近 3 个批次。RAND 的“非涉华”历史样本 `2658` 位于批次 `747`，不在当前页面入口中；数据库核对确认其 `error` 与 `relevance_reason` 完全一致，前端按去重分支直接展示。未为页面验收伪造或修改历史数据。
- 桌面和 390×844 移动端均无页面级横向溢出；候选表在移动端使用既有内部横向滚动。走查没有非 GET 请求、控制台错误或页面异常。走查后 `LLM_OUTBOUND_ENABLED=false`、授权总数和有效授权数均为 0、本地验收队列与 `unacked` 均为 0。
- 结构化证据和截图保存在 `.codex-backups/20261007-candidate-error-summary/candidate-error-walkthrough.json`、`atlantic-candidate-2942-summary.png`、`rand-candidate-3022-summary.png` 和 `rand-candidate-3022-mobile.png`。

### 正式本地部署（2026-10-08）

- 部署前两次确认 Worker 活动任务、预留任务、Redis 默认队列和 `unacked` 均为 0；`LLM_OUTBOUND_ENABLED=false`，授权总数和有效授权数均为 0。
- 使用当前代码重建并替换 `frontend` 容器，仅重启空闲的 `celery-worker` 以载入后端摘要规则。Backend 继续使用既有源码热挂载；Beat、PostgreSQL、Redis 和 MinIO 未重启，也未执行数据库迁移。
- 正式前端 `http://localhost:3000/settings` 与后端 `http://localhost:8000/docs` 均返回 HTTP 200，Worker ping 正常。Worker 容器内直接调用无前缀 HTTP 404 样本，返回“报告正文地址请求失败：返回 HTTP 404。”。
- 正式页面只读回归再次验证 Atlantic Council 候选 `2942` 和 RAND 候选 `3022` 的摘要、折叠与展开状态；桌面和 390×844 移动端无页面级横向溢出。请求全部为 GET/HEAD/OPTIONS，浏览器控制台无错误或异常。
- 部署后 18:25（北京时间）自然调度中，采集 `selected_count=0`，AI 分块调度返回空列表。最终活动任务、预留任务、队列、`unacked`、授权总数和有效授权数均为 0，外发总开关保持关闭。
- 正式回归证据保存在 `.codex-backups/20261007-candidate-error-summary/candidate-error-production-walkthrough.json`、`production-atlantic-candidate-2942-summary.png`、`production-rand-candidate-3022-summary.png` 和 `production-rand-candidate-3022-mobile.png`。

### 移动端候选详情布局（2026-10-08）

- 在不复制数据视图的前提下，为采集批次和候选表格补充语义字段标签；宽度不超过 820px 时，同一份表格转为纵向信息行，桌面端继续保持原表格布局。
- 移动候选按“标题、状态、跳过原因、类型、页数、涉华、链接、说明、操作”顺序展示，说明摘要与授权按钮不再位于横向表格右侧。采集批次的时间、状态、数量、质量摘要和“查看候选”操作也改为纵向布局。
- 修正原有 `760px` 采集表、`920px` 候选表和质量摘要 `260px` 最小宽度在移动端的级联优先级。390×844 验收中，文档宽度为 390px，采集表 `clientWidth/scrollWidth=290/290`，候选表为 `264/264`，均不需要横向滚动。
- RAND 候选 `3022` 的 9 个可见字段标签与 `data-label` 全部一致，说明区左右边界为 `63/327px`，完整位于 390px 视口内；Atlantic Council 候选 `2942` 的错误摘要和详情展开行为保持不变。
- Prettier、TypeScript、ESLint 和 Next.js 生产构建通过。部署前后外发总开关均关闭，授权、Worker 活动/预留任务、Redis 默认队列和 `unacked` 均为 0；正式前后端均返回 HTTP 200。
- 隔离和正式页面回归都没有非 GET/HEAD/OPTIONS 请求、控制台错误或页面异常。证据保存在 `.codex-backups/20261008-mobile-candidate-layout/mobile-candidate-walkthrough.json`、`mobile-candidate-production-walkthrough.json`、`rand-candidate-3022-mobile-overview.png`、`rand-candidate-3022-mobile-note.png` 及对应 `production-` 截图。

### 移动端顶部导航（2026-10-08）

- 560px 以下的主导航由横向滚动改为固定四列，“仪表盘、研究报告、通知提醒、系统设置”始终等宽完整显示；桌面和平板断点保持原样。
- 未读通知数量改为导航项右上角小角标，并为文字预留垂直空间。390px 下每列宽 `88.5px`，320px 下每列宽 `71px`；两种宽度下角标与“通知提醒”均不重叠。
- 390px 和 320px 验收中，文档、顶部栏和导航的 `scrollWidth` 均不超过 `clientWidth`；四个标签均完整，`系统设置` 活动态正确。320px 下品牌副标题自然换行，用户操作区正常换行，无元素遮挡。
- 验收脚本不再写死未读数量，只验证角标存在且为正整数。正式回归时未读数量由 189 自然增加到 190，布局和角标检查均通过。
- Prettier、TypeScript、ESLint 和 Next.js 生产构建通过；隔离及正式回归均无非 GET/HEAD/OPTIONS 请求、控制台错误或页面异常。部署后外发关闭，授权、活动/预留任务、队列和 `unacked` 均为 0，正式前后端返回 HTTP 200。
- 证据保存在 `.codex-backups/20261008-mobile-top-nav/mobile-top-nav-walkthrough.json`、`mobile-top-nav-production-walkthrough.json`、`mobile-top-nav-390.png`、`mobile-top-nav-320.png` 及对应 `production-` 截图。

### 移动端报告详情顺序与导航（2026-10-08）

- 基线走查确认报告详情内部在 390px 和 320px 下均无横向溢出，问题来自移动端仍按“列表、详情”排列：report 382 的详情分别位于页面约 7,628px 和 9,424px 之后。
- 选中报告后，820px 以下改为优先排列详情；详情顶部增加“返回报告列表”锚点，从列表选择报告后自动将详情定位到粘性顶栏下方。未选中报告时仍先显示筛选和列表，桌面端继续保持左侧列表、右侧详情的双栏布局。
- 390px 和 320px 真实页面回归均验证详情位于列表之前、返回列表与重新选择报告定位正确、内容标签保持两列换行且页面无横向溢出；1365px 下移动导航隐藏，双栏布局保持不变。
- Prettier、TypeScript、ESLint 和 Next.js 生产构建通过，未引入依赖。隔离和正式回归均没有非 GET/HEAD/OPTIONS 请求、控制台错误或页面异常。
- 正式环境仅重建并替换 `frontend` 容器，未重启后端、Worker、Beat、PostgreSQL、Redis 或 MinIO，也未执行迁移。部署后前后端 HTTP 200，`LLM_OUTBOUND_ENABLED=false`，授权总数和有效授权数均为 0，Worker 活动/预留任务、Redis 默认队列和 `unacked` 均为 0。
- 基线、隔离及正式回归证据保存在 `.codex-backups/20261008-mobile-report-detail/`，结构化结果分别为 `mobile-report-detail-baseline.json`、`mobile-report-detail-postchange.json` 和 `mobile-report-detail-production.json`。

### 移动端长文阅读区（2026-10-08）

- 使用 report 444（主要观点 2,000 字、深层研判 2,108 字、全文翻译 115,325 字、原文正文 320,311 字）进行真实长文本走查。修改前 390px 和 320px 下全文翻译分别把阅读区撑到约 194,459px 和 240,167px，深入阅读后内容标签离开视口约 3,174px；切换内容时页面会停留在新内容中后段。
- 820px 以下的正文阅读区改为最高 `64svh`，保留 `64vh` 兼容回退，并使用独立纵向滚动和滚动边界约束。切换主要观点、深层研判、全文翻译、原文正文或切换报告时，阅读区内部滚动位置自动归零。
- 内容标签与当前面板补充稳定的 `id`、`aria-controls`、`aria-labelledby` 和 `tabpanel` 关系；正文面板可获得键盘焦点。复制、导出、数据请求和报告状态逻辑未改变。
- 390px 和 320px 隔离及正式回归中，阅读区可视高度均约 538px，内部滚动到 3,000px 后标签保持可见，切换到主要观点后 `scrollTop=0`。页面总高度由约 20–25 万 px 降到约 1.0–1.2 万 px，且无横向溢出。
- 1365px 桌面端继续使用原有 `72vh` 阅读框（约 648px），独立滚动和切换复位正常。Prettier、TypeScript、ESLint、Next.js 生产构建及 `git diff --check` 均通过，未引入依赖。
- 正式环境仅重建并替换 `frontend` 容器。正式回归没有非 GET/HEAD/OPTIONS 请求、控制台错误或页面异常；部署后前后端 HTTP 200，外发关闭、授权总数和有效授权数均为 0，Worker 活动/预留任务、Redis 默认队列和 `unacked` 均为 0。
- 证据保存在 `.codex-backups/20261008-mobile-long-reading/`，包括 `mobile-long-reading-baseline.json`、`mobile-long-reading-postchange.json`、`mobile-long-reading-production.json` 及对应截图。

### 移动端复核、授权与导出操作区（2026-10-09）

- 使用 report 444 的管理员视图走查复核、维护、复制、导出和全文生成授权。复核快捷按钮仍保留原有大触控区域和即时更新逻辑，本轮没有点击或修改任何复核状态、意见或报告数据。
- 560px 以下的管理员维护、成果导出和复制按钮统一为整行宽度，解决窄屏按钮宽度不一、换行位置零散的问题；桌面端继续使用原有横向按钮布局。
- 授权弹窗首屏仅展示文档、字符数、发送范围和外发总开关；服务类型、服务端点、模型和文档版本完整保留在默认收起的“服务与文档版本”详情中。技术信息没有删除，也没有改变授权匹配或提交逻辑。
- 640px 以下弹窗覆盖浏览器默认最大宽度限制，320px 下实际宽度由 282px 增至 304px；弹窗操作按钮改为整行宽度。默认视图中同意区可见，授权复选框保持未勾选，“确认授权”保持禁用。
- 390px、320px 和 1365px 隔离及正式回归均无页面或控件横向溢出；主信息四项、技术信息四项均可访问。所有浏览器请求均为 GET/HEAD/OPTIONS，未授权、未撤销、未复核、未导出，控制台无错误或异常。
- 验收期间 Docker Desktop 曾处于停止状态，恢复后 Compose 服务按既有重启策略启动；自然调度触发的一次 `crawl.all_sources` 完成且队列恢复为空后才部署。正式环境仅重建并替换 `frontend` 容器，未迁移数据库或手动投递任务。
- Prettier、TypeScript、ESLint、Next.js 生产构建和 `git diff --check` 均通过。部署后前后端 HTTP 200，`LLM_OUTBOUND_ENABLED=false`，授权总数和有效授权数为 0，Worker 活动/预留任务、Redis 默认队列和 `unacked` 均为 0。
- 证据保存在 `.codex-backups/20261008-mobile-review-actions/`，包括 `mobile-review-actions-baseline.json`、`mobile-review-actions-postchange.json`、`mobile-review-actions-production.json` 及对应截图。

### 移动端复核历史与 AI 分块进度（2026-10-09）

- 使用 report 356 的 3 条真实复核事件和 report 382 的 94 个真实 AI 分块进行只读走查；report 382 包含 3 个失败翻译分块。本轮未修改复核、报告或分块数据。
- 复核历史由连续文本列表改为编号时间线，状态、时间、操作人和备注分层展示；状态使用与含义一致的成功、警告和危险色，长邮箱及备注可安全换行。
- AI 总进度改为“已完成、失败、运行中”三项指标；分析笔记和全文翻译分别展示成功数及待处理、已入队、处理中、失败明细，失败数保持醒目。
- 完整分块改为结构化状态行，保留类型、序号、总数、状态、重试次数和失败详情。移动端列表最大高度为 `64svh`（`64vh` 回退），桌面为 `32rem`，并提供独立滚动；展开文案会切换为“收起全部分块”。
- 修改前 320px 下 94 条列表高约 4,941px；修改后 320px 和 390px 的可视高度均约 538px，94 条记录及 3 条失败详情仍可访问。两种宽度均无页面横向溢出。
- Prettier、TypeScript、ESLint 和 Next.js 生产构建通过，未引入依赖。隔离与正式回归均只有 GET/HEAD/OPTIONS 请求，控制台无错误或页面异常。
- 正式环境仅重建并替换 `frontend` 容器，未重启后端、Worker、Beat、PostgreSQL、Redis 或 MinIO，也未执行迁移。部署后前后端 HTTP 200，`LLM_OUTBOUND_ENABLED=false`，授权总数和有效授权数为 0，Worker 活动/预留任务、Redis 默认队列和 `unacked` 均为 0。
- 备份、基线、隔离和正式验收证据保存在 `.codex-backups/20261009-mobile-history-progress/`；结构化结果为 `mobile-history-progress-baseline.json`、`mobile-history-progress-post.json` 和 `mobile-history-progress-formal.json`，并附对应截图。

### 移动端搜索、待复核列表与报告切换（2026-10-09）

- 使用正式库 291 篇“待复核 + AI 已完成 + 成果齐全”报告建立真实待老师复核列表；使用 report 382 验证关键词搜索，使用 report 446 和 445 验证列表切换及详情定位。所有操作均为只读，未勾选批量动作或修改报告状态。
- 560px 以下的关键词输入保持常驻，搜索与重置按钮改为两列；四个工作流快捷入口由单列改为两列。存在关键词时“清空搜索”仍可见，完整重置入口保留。
- 820px 以下的高级筛选和批量操作默认收起，摘要持续显示总报告数、页码、本页数量及已选数量。展开后六项筛选、上一页/下一页、全选、批量复核及两种批量导出操作完整保留。
- 移动端隐藏与行动状态重复的流程标签，并将超长报告标题限制为最多四行；桌面端继续显示完整标题和流程标签，筛选与批量区也保持直接展开。
- 修改前 320px 下默认列表首条报告距控制区顶部约 1,405px，待复核列表约 1,572px；修改后分别约 440px 和 607px。待复核长标题样本卡片由约 447px 降为 328px。
- 正式回归中，“待老师复核”仍返回 291 篇；关键词 `382` 返回唯一的 report 382；点击 report 445 后当前激活报告为 445。320px 和 390px 均无横向溢出，1365px 桌面端折叠按钮隐藏且原筛选、批量区可见。
- Prettier、TypeScript、ESLint、Next.js 生产构建和 `git diff --check` 均通过，未引入依赖。隔离与正式验收均只有 GET/HEAD/OPTIONS 请求，控制台无错误或页面异常。
- 正式环境仅重建并替换 `frontend` 容器，未重启后端、Worker、Beat、PostgreSQL、Redis 或 MinIO，也未执行迁移。部署后前后端 HTTP 200，`LLM_OUTBOUND_ENABLED=false`，授权总数和有效授权数为 0，Worker 活动/预留任务、Redis 默认队列和 `unacked` 均为 0。
- 备份、基线、隔离与正式验收证据保存在 `.codex-backups/20261009-mobile-report-list/`；结构化结果为 `mobile-report-list-baseline.json`、`mobile-report-list-post.json` 和 `mobile-report-list-formal.json`，并附对应截图。

### 移动端详情标题、来源与成果概览（2026-10-09）

- 使用 report 445（Atlantic Council 长标题、成果 3/3）、report 447（Guardian Tiger III，成果 2/3、AI 失败但评论/翻译可读）和 report 356（已通过复核、成果 3/3）进行真实详情页走查。所有操作均为只读，未修改复核、授权、导出或报告数据。
- 560px 以下将详情标题区压缩为“ID + 打开原文”同排、标题完整保留、来源与状态紧凑展示；桌面端标题、来源、状态布局保持原样。320px 下 report 445 标题区高度由约 458px 降为约 302px。
- 移动端隐藏与状态字段重复的阅读说明段落和成果概览说明步骤，保留复核状态、AI 状态、成果状态、下一步入口和全部交付按钮。320px 下阅读提示区由约 525px 降为约 206px。
- 成果概览在移动端改为更紧凑的卡片行，复制评论稿、导出 Word、导出 Markdown、复制全文翻译及三项阅读入口全部保留。320px 下成果概览高度由约 1,025-1,050px 降为约 679px。
- 正式回归中，详情顶部到正文阅读区的距离在 320px 下由约 2,067-2,132px 降为 1,259-1,291px，在 390px 下为 1,136-1,187px；320px、390px 和 1365px 均无横向溢出。
- Prettier、TypeScript、ESLint、Next.js 生产构建和 `git diff --check` 均通过，未引入依赖。隔离与正式验收均只有 GET/HEAD/OPTIONS 请求，控制台无错误或页面异常。
- 本轮开始时 Docker Desktop 未运行；普通启动后 Compose 服务按既有重启策略恢复。正式部署阶段仅重建并替换 `frontend` 容器，未重建后端、Worker、Beat、PostgreSQL、Redis 或 MinIO，也未执行迁移。
- 部署后前后端 HTTP 200，`LLM_OUTBOUND_ENABLED=false`，授权总数和有效授权数为 0，Worker 活动/预留任务、Redis 默认队列和 `unacked` 均为 0。验收用 headless Edge 已关闭，`3001/9241` 无监听，正式 `3000/8000` 保持可用。
- 备份、基线、隔离与正式验收证据保存在 `.codex-backups/20261009-mobile-detail-overview/`；结构化结果为 `mobile-detail-overview-baseline.json`、`mobile-detail-overview-post.json` 和 `mobile-detail-overview-formal.json`，并附对应截图。

### 移动端正文标签与当前内容操作区（2026-10-09）

- 使用 report 445（四项正文均可读）和 report 447（主要观点未生成、深层研判/全文翻译/原文正文可读）进行真实正文区走查。所有操作均为只读，未触发复制、导出、复核、授权或 AI 任务。
- 560px 以下将正文区标题和“复制当前内容”压缩到同一行，隐藏重复说明段落；四个正文标签改为稳定两列紧凑网格，保留“主要观点、深层研判、全文翻译、原文正文”和字数/未生成状态。
- 正文区补充移动端 `scroll-margin-top`，从成果概览或脚本定位到正文时，标题、复制按钮和标签不再被顶部粘性导航遮住；桌面端标题说明、按钮和横向标签布局保持原样。
- 正式回归中，320px 下正文相对阅读区顶部距离由约 366-391px 降为约 208px，节省 157-182px；390px 下由约 366px 降为约 208px，节省约 157px。320px、390px 和 1365px 均无横向溢出。
- report 447 的“主要观点未生成”空态在正式 320px 下完整展示，“复制当前内容”保持禁用；report 445 的主要观点、深层研判、全文翻译和原文正文标签及正文阅读框均可见。
- Prettier、TypeScript、ESLint、Next.js 生产构建、Docker 前端镜像构建和 `git diff --check` 均通过，未引入依赖。隔离与正式验收均只有 GET/HEAD/OPTIONS 请求，控制台无错误或页面异常。
- 正式环境仅重建并替换 `frontend` 容器，未重建后端、Worker、Beat、PostgreSQL、Redis 或 MinIO，也未执行迁移。部署后前后端 HTTP 200，`LLM_OUTBOUND_ENABLED=false`，授权总数和有效授权数为 0，Worker 活动/预留任务、Redis 默认队列和 `unacked` 均为 0。
- 验收用 headless Edge 与隔离 `3001` 预览服务均已关闭，正式 `3000/8000` 保持可用。备份、基线、隔离与正式验收证据保存在 `.codex-backups/20261009-mobile-content-tabs/`；结构化结果为 `mobile-content-tabs-baseline.json`、`mobile-content-tabs-post.json` 和 `mobile-content-tabs-formal.json`，并附对应截图。
