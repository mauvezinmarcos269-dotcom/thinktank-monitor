# 来源准入与试运行状态

更新时间：2026-10-03

本文档记录当前代码中 `source_rollout_policy` 的实际口径，用于区分“机构重要性”和“是否允许进入自动入库试运行”。机构优先级高不等于已经可以批量入库；只有完成小样本文档复核并通过策略层校验的来源，才允许进入 `pilot_crawl`。

## 状态定义

| 状态 | 含义 | 自动入库试运行 |
| --- | --- | --- |
| `pilot_crawl` | 已通过真实小样本文档复核，可小批量写入报告库 | 允许 |
| `discovery_only` | 只保留候选发现和只读审计结果，暂不进入批量入库 | 不允许 |
| `blocked` | 当前入口不可稳定访问或抓取受站点防护影响 | 不允许 |
| `standard_review` | 尚未完成小样本文档复核 | 不允许 |

## 文档口径

| 文档策略 | 含义 |
| --- | --- |
| `pdf_20_page_required` | 优先要求 PDF，页数一般不少于 20 页 |
| `web_article_allowed` | 来源可接受足够长、报告型网页正文进入候选审计；是否自动入库仍取决于 rollout 状态 |
| `source_access_blocked` | 当前来源入口不可稳定访问，需先确认可访问入口、官方 feed、授权 API 或人工维护方式 |

## 当前代码状态

| key | 来源 | 机构层级 | rollout 状态 | 文档策略 | 自动入库试运行 | 当前处理 |
| --- | --- | --- | --- | --- | --- | --- |
| `brookings` | Brookings Institution | P0 | `pilot_crawl` | `pdf_20_page_required` | 允许 | 10 篇历史样本已全部复核通过；2026-10-02 最新网站源 run 743 前端候选摘要走查通过，3 条重复，正常批次无需人工处理；继续每次最多新增 1 篇 |
| `carnegie` | Carnegie Endowment for International Peace | P0 | `pilot_crawl` | `pdf_20_page_required` | 允许 | report 440 已完成 AI 生成与人工复核通过；2026-10-02 最新网站源 run 745 前端候选摘要走查通过，1 条重复，正常批次无需人工处理；继续每次最多新增 1 篇并人工复核 |
| `cfr` | Council on Foreign Relations | P0 | `pilot_crawl` | `pdf_20_page_required` | 允许 | 5 篇历史 PDF 样本已全部复核通过；2026-10-02 最新网站源 run 737 候选摘要筛选走查通过，5 条重复、1 条短 PDF；来源总览“需处理：正常”误提示已修复并验证；继续每次最多新增 1 篇 |
| `csis` | Center for Strategic and International Studies | P0 | `pilot_crawl` | `pdf_20_page_required` | 允许 | 主入口 4 篇 PDF 样本已复核通过；2026-10-02 最新主入口 run 741 前端候选摘要走查通过，2 条重复、2 条短 PDF；继续每次最多新增 1 篇 |
| `piie` | Peterson Institute for International Economics | P0 | `pilot_crawl` | `pdf_20_page_required` | 允许 | 4 篇历史 PDF 样本已全部复核通过；2026-10-02 最新网站源 run 738 前端候选摘要走查通过，4 条重复，正常批次无需人工处理；继续每次最多新增 1 篇 |
| `rand` | RAND Corporation | P0 | `pilot_crawl` | `pdf_20_page_required` | 允许 | report 439 已完成 AI 生成与人工复核通过；2026-10-02 最新网站源 run 744 前端候选摘要走查通过，7 条重复、2 条无 PDF；继续每次最多新增 1 篇并人工复核 |
| `aei` | American Enterprise Institute | P1 | `pilot_crawl` | `web_article_allowed` | 允许 | 8 篇入库样本已全部复核通过；356 已补抓 Asia Society 原始全文并重跑 AI；继续每次最多新增 1 篇并人工复核 |
| `atlantic_council` | Atlantic Council | P1 | `pilot_crawl` | `pdf_20_page_required` | 允许 | report 344、441、442 已完成 AI 生成与人工复核通过；正式 pilot 试抓已通过策略守卫，本轮未新增；继续每次最多新增 1 篇并人工复核 |
| `ecfr` | European Council on Foreign Relations | P2 | `pilot_crawl` | `web_article_allowed` | 允许 | 3 篇受控样本已全部复核通过，覆盖 PDF 和网页长文；继续每次最多新增 1 篇并人工复核 |
| `cap` | Center for American Progress | P1 | `blocked` | `source_access_blocked` | 不允许 | 需先确认稳定入口或可授权访问方式 |
| `cato` | Cato Institute | P1 | `blocked` | `source_access_blocked` | 不允许 | 普通 HTTP 抓取受站点防护影响，暂缓自动化 |
| `heritage` | The Heritage Foundation | P1 | `blocked` | `source_access_blocked` | 不允许 | 需先确认稳定入口、官方 feed 或人工维护入口 |
| 其他来源 | - | P0-P4 | `standard_review` | `pdf_20_page_required` | 不允许 | 进入入库前必须先完成只读审计和人工确认 |

## 老师重点名单中的待审计来源

以下来源来自老师附件，属于优先接入规划，但尚不代表当前代码已配置专用解析器或已允许自动入库。接入前仍需按 [source-onboarding-playbook.md](source-onboarding-playbook.md) 完成入口确认、只读审计、小样本复核和 rollout 策略更新。

| 建议 key | 来源 | 机构层级 | 规划状态 | 建议文档策略 | 自动入库试运行 | 下一步处理 |
| --- | --- | --- | --- | --- | --- | --- |
| `hoover` | Hoover Institution | P1 | `standard_review` | `pdf_20_page_required` | 不允许 | 确认稳定出版物入口，评估长报告数量和可下载性 |
| `wilson-center` | Wilson Center | P1 | `standard_review` | `pdf_20_page_required` | 不允许 | 确认报告入口，区分长报告、评论、活动页面 |
| `nber` | National Bureau of Economic Research | P1 | `standard_review` | `pdf_20_page_required` | 不允许 | 核验工作论文页可达性、页数和涉华筛选规则 |
| `bruegel` | Bruegel | P2 | `standard_review` | `pdf_20_page_required` | 不允许 | 审计出版物入口，确认 China/EU-China 相关长报告比例 |
| `chatham-house` | Chatham House | P2 | `standard_review` | `pdf_20_page_required` | 不允许 | 复核已有解析能力与当前页面结构，补足小样本审计 |
| `cepr` | Centre for Economic Policy Research | P2 | `standard_review` | `pdf_20_page_required` | 不允许 | 确认报告/政策洞察入口，避免短新闻或会议内容混入 |
| `ifo` | ifo Institute | P2 | `standard_review` | `pdf_20_page_required` | 不允许 | 确认英文研究报告入口和 PDF 长度规则 |
| `ifri` | French Institute of International Relations | P2 | `standard_review` | `pdf_20_page_required` | 不允许 | 确认英文/法文报告入口，优先评估英文涉华长报告 |
| `jiia` | Japan Institute of International Affairs | P3 | `standard_review` | `pdf_20_page_required` | 不允许 | 确认英文出版物入口和中国/印太专题筛选方式 |
| `rieti` | Research Institute of Economy, Trade and Industry | P3 | `standard_review` | `pdf_20_page_required` | 不允许 | 核验英文论文/报告入口，排除短摘要页 |
| `eria` | Economic Research Institute for ASEAN and East Asia | P3 | `standard_review` | `pdf_20_page_required` | 不允许 | 确认出版物入口，重点抽查区域经济和供应链涉华报告 |

## 待确认或去重条目

| 附件名称 | 当前处理 | 原因 |
| --- | --- | --- |
| Peter G. Peterson / IIE | 暂按 `piie` 合并 | 与 Peterson Institute for International Economics 高度疑似重复，当前 PIIE 已进入 `pilot_crawl` |
| Leibniz Institute | 暂不建 key | 名称过泛，需要老师确认完整英文名、官网和目标报告栏目 |
| German Institute / Deutsches Institut | 暂不建 key | 名称过泛，可能指向多个德国研究机构，需要先人工确认 |

## 开发规则

1. 不因为来源属于 P0/P1 就默认进入 `pilot_crawl`。
2. 不因为解析器能发现候选就默认写入报告库。
3. `discovery_only` 来源可以用于解析器调试、候选发现和质量统计，但不能通过 `pilot_crawl_sources` 写入正式报告。
4. `web_article_allowed` 只表示该来源允许网页长文作为候选文档形态，不等于已经允许自动入库。
5. 老师重点名单提高接入优先级，但不跳过只读审计、小样本复核和人工验收。
6. 调整任一来源 rollout 状态前，应先留下只读审计结果，并同步更新本文档、`source_rollout_policy.py` 和相关测试。
7. 具体接入、试抓、复核、升级和停用步骤按 [source-onboarding-playbook.md](source-onboarding-playbook.md) 执行。
8. `pilot_crawl_sources` 的默认来源只能包含已放行且样本稳定的 `pilot_crawl` 来源；不得包含 `blocked`、`discovery_only` 或尚未复核的 `standard_review` 来源。

## 2026-09-30 RAND 二次受控试写与升级

只读复核：

- 执行 `poetry run python -m app.scripts.audit_source_documents --keys rand --max-candidates 5 --discovery-timeout 90 --document-timeout 120`。
- RAND 本轮发现 9 条原始候选、9 条去重候选，抽查 5 条文档全部通过。
- 抽样均为标题显性涉华的 PDF 长报告，页数分别为 113、23、71、64、40 页。

受控试写：

- 执行 `poetry run python -m app.scripts.pilot_crawl_sources --keys rand --allow-standard-review --max-saved 1 --max-candidates 5 --ai-status skipped`。
- `crawl_run_id=724`，`source_id=7`，检查候选 5 条，新增入库 1 条。
- 新增 `report_id=439`：`The Scope and Nature of the U.S.-China Competition`，PDF 113 页，非空页 108 页，正文约 320,311 字符。
- 新增报告初始为 `crawl_status=success`、`ai_status=skipped`、`review_status=pending_review`。

AI 与人工复核：

- 已对 report 439 触发 AI 生成，130 个分块全部完成，失败 0 个。
- 生成全文翻译约 115,462 字符，主要观点约 1,570 字符，深层研判约 2,384 字符。
- 主要观点包含 4 个分论点，深层研判包含 5 个分论点，符合当前交付口径。
- report 439 已标记为 `approved`，复核意见记录翻译术语后续可人工润色，但不影响本轮自动化流程验收。

判断：

- RAND 涉华过滤修复后的二次试写样本质量明显优于首次试写，未再保存不明显涉华报告。
- RAND 已完成“只读复核 -> 受控试写 -> AI 生成 -> 人工通过”的完整闭环。
- 代码 rollout 已升级为 `pilot_crawl`，文档策略保持 `pdf_20_page_required`。
- 升级后仍保持每次最多新增 1 篇和前端人工复核，不扩大抓取规模。

## 2026-10-01 RAND 正式 pilot_crawl 试抓

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.pilot_crawl_sources --keys rand --max-saved 1 --max-candidates 5 --ai-status skipped
```

运行结果：

- `crawl_run_id=725`，`source_id=7`。
- 未使用 `--allow-standard-review`，说明 RAND 已能通过 `pilot_crawl` 策略守卫。
- 本轮发现候选 5 条，新增入库 0 条。
- 5 条候选均被正确标记为 `duplicate_existing`，对应已入库或已发现过的 RAND 涉华报告。

判断：

- RAND 升级后的正式试抓链路有效，未出现误放行、解析失败或非涉华报告入库。
- 本轮没有新增报告并非异常，而是去重逻辑按预期生效。
- 后续 RAND 可纳入常规小批量试运行，但仍建议保持每次最多新增 1 篇，并继续人工复核新增样本。

## 2026-10-02 RAND run 744 前端候选摘要走查

走查对象：

- RAND website 来源 `source_id=7`，URL `https://www.rand.org/`。
- 最新网站源运行 `crawl_run_id=744`，运行状态 `success`。
- 运行时间：2026-10-02 11:00:06，耗时 7 秒。

后端统计：

- 候选总数 9 条，新增入库 0 条。
- 跳过原因：`已入库重复` 7 条，`未发现 PDF 链接` 2 条。
- 内容类型当前均为 `未知类型`，原因是这些候选未进入正式 PDF 文档入库阶段；不影响跳过原因统计。

前端实际页面走查：

- 设置页中精确打开 RAND website 来源，而非 RAND RSS 来源。
- 最新运行确认为 `crawl_run_id=744`，摘要卡片初始显示：全部候选 9、新增入库 0、无 PDF 2、短 PDF 0、已入库重复 7。
- 逐个点击摘要卡片后，筛选汇总与候选表格行数一致：
  - 全部候选：当前显示 9 条，表格 9 行。
  - 新增入库：当前显示 0 条，表格 0 行，并显示“当前筛选条件下暂无候选”。
  - 无 PDF：当前显示 2 条，表格 2 行，行内原因均为“未发现 PDF 链接 / 文档检查”。
  - 短 PDF：当前显示 0 条，表格 0 行，并显示空结果提示。
  - 已入库重复：当前显示 7 条，表格 7 行，行内原因均为“已入库重复 / 重复候选”。
- 浏览器控制台和网络检查未发现前端错误。

判断：

- RAND 网站源最新正式试运行结果可解释，未出现重复入库、误保存或筛选统计错位。
- 与 Atlantic Council run 735 的候选展示口径一致：重复、无 PDF、短 PDF 和 0 条筛选都能在前端清晰区分。
- RAND 继续保持 `pilot_crawl` + `pdf_20_page_required`，仍建议每次最多新增 1 篇，并对新增样本做前端人工复核。

## 2026-10-02 CSIS run 741 前端候选摘要走查

走查对象：

- CSIS active website 主入口 `source_id=5`，URL `https://www.csis.org/analysis`。
- 最新主入口运行 `crawl_run_id=741`，运行状态 `success`。
- 运行时间：2026-10-02 10:58:50，耗时 60 秒。
- 已停用的 CSIS RSS 来源和重复 website 来源未参与本轮走查。

后端统计：

- 候选总数 4 条，新增入库 0 条。
- 跳过原因：`PDF 页数不足` 2 条，`已入库重复` 2 条。
- 两条短 PDF 样例分别为 11 页和 15 页，均低于 20 页门槛。

前端实际页面走查：

- 设置页中精确打开 CSIS 主入口 `https://www.csis.org/analysis`。
- 最新运行确认为 `crawl_run_id=741`，摘要卡片初始显示：全部候选 4、新增入库 0、无 PDF 0、短 PDF 2、已入库重复 2。
- 逐个点击摘要卡片后，筛选汇总与候选表格行数一致：
  - 全部候选：当前显示 4 条，表格 4 行。
  - 新增入库：当前显示 0 条，表格 0 行，并显示“当前筛选条件下暂无候选”。
  - 无 PDF：当前显示 0 条，表格 0 行，并显示空结果提示。
  - 短 PDF：当前显示 2 条，表格 2 行，行内原因均为“PDF 页数不足 / 文档门槛”。
  - 已入库重复：当前显示 2 条，表格 2 行，行内原因均为“已入库重复 / 重复候选”。
- 浏览器控制台和网络检查未发现前端错误。

判断：

- CSIS 主入口最新正式试运行结果可解释，短 PDF 和重复候选均被正确拆分展示。
- 与 Atlantic Council run 735、RAND run 744 的候选展示口径一致；0 条筛选不会隐藏摘要区，老师可以继续点回其他原因卡片复查。
- CSIS 继续保持 `pilot_crawl` + `pdf_20_page_required`，后续只保留 `/analysis` 主入口参与小批量试运行。

## 2026-10-02 CFR run 737 前端候选摘要走查

走查对象：

- CFR website 来源 `source_id=3`，URL `https://www.cfr.org/`。
- 最新网站源运行 `crawl_run_id=737`，运行状态 `success`，耗时 7 秒。

后端统计：

- 候选总数 6 条，新增入库 0 条。
- 跳过原因：`已入库重复` 5 条，`PDF 页数不足` 1 条。
- 短 PDF 为 `Dismantling China’s Supply-Chain Weapon`，检查说明记录为 14 页，低于 20 页门槛。

前端实际页面走查：

- 设置页中精确打开 CFR website 最新运行，通过网络请求确认 `crawl_run_id=737`。
- 摘要卡片初始显示：全部候选 6、新增入库 0、无 PDF 0、短 PDF 1、已入库重复 5。
- 逐个点击五张卡片，筛选总数、当前显示数量和候选表格数据行数均一致，分别为 6、0、0、1、5。
- 新增入库和无 PDF 的 0 条筛选均保留摘要区及筛选控件，并显示“当前筛选条件下暂无候选”。
- 短 PDF 行内原因为“PDF 页数不足 / 文档门槛”，说明保留“14 页，要求至少 20 页”；重复行原因为“已入库重复 / 重复候选”。
- 从重复筛选切回全部候选后，表格恢复为 6 行。
- 浏览器控制台和网络检查未发现错误；已保存桌面截图及逐卡片核对记录。

走查观察与后续处理：

- 首次走查发现来源总览显示“需处理：正常”。原 `getSourceReviewReason` 将“有候选但未入库”的来源一律列入需处理，即使该来源已经准入、抓取成功且 `diagnosis_code=ok`。
- 用户确认后已修复：正常重复和短 PDF 批次不再列入需处理，来源提示与筛选数量已在实际页面验证，详见下一节。
- 首次走查时短 PDF 候选的 `page_count` 和 `content_kind` 接口字段为空，14 页信息仅保留在检查说明中；后续已完成元数据保留与历史展示补齐，CFR 表格现在显示“14 / PDF”，详见后文。

判断：

- CFR 最新批次的候选摘要筛选和修复后的来源总览处理提示均通过验收。
- CFR 继续保持 `pilot_crawl` + `pdf_20_page_required`，每次最多新增 1 篇并人工复核。
- 本轮未触发新采集、AI 生成或报告复核状态变更。

## 2026-10-02 来源需处理误提示修复

用户确认的处理口径：

- 已准入、已校对、健康状态正常且本轮抓取成功的来源，仅当全部有效候选都因重复或 PDF 不足 20 页跳过时，排除出需处理列表。
- 无 PDF、PDF 获取或解析失败、文本不足、涉华判断异常、其他未解释的跳过，以及尚未完成准入或校对的来源继续保留。

实现：

- `settings-page-utils.ts` 中统一解析本轮质量摘要，供抓取记录展示和需处理判断共同使用。
- 只有明确的重复与短 PDF 原因、且计数覆盖全部有效候选时，才认定为正常跳过；来源内去重不计入有效候选数量。
- 后端诊断为 `ok` 但本轮未通过上述检查时，提示改为“有候选但未入库”，避免“需处理：正常”。
- 抓取中的批次优先显示“抓取仍在运行”。

验证：

- 26 个针对性逻辑检查通过，覆盖正常重复、短 PDF、来源内去重计数、异常混合、摘要缺失、运行中、待准入及待校对等场景。
- 当前 56 个来源中，需处理数量由 53 降至 48；排除的是 Brookings、CFR、CSIS、Carnegie、PIIE 的正常网站批次。
- 实际页面中“需处理”按钮、列表数量和逐项来源均一致；CFR 显示“当前无需人工处理，继续观察自动抓取结果”。
- 缺少 PDF、涉华筛选未通过的批次，以及 Brookings / RAND 的失败 RSS 来源仍保留在需处理列表。
- CFR run 737 五张候选卡片再次点击验证通过，表格行数分别为 6、0、0、1、5；抓取记录摘要的指标和跳过标签展示正常。
- `npm run typecheck`、`npm run lint` 和相关文件的 `git diff --check` 通过；浏览器控制台及网络未发现错误。
- 修改前备份、逻辑核对结果、页面核对结果和截图保存在 `.codex-backups/source-review-reason-20261002-223610/`。

## 2026-10-02 短 PDF 候选元数据保留与历史展示补齐

问题：

- 文档提取完成后，短 PDF 校验抛出普通 `ValueError`，采集流程只保存错误文字，未将已知的页数、类型和 PDF 地址保存到候选。

处理：

- 新增兼容 `ValueError` 的 `ReportDocumentValidationError`，在页数或有效文本校验未通过时携带已提取的文档结果。
- 候选跳过处理保存错误中的 PDF 元数据；普通采集和受控试运行共用 `set_candidate_document_metadata`，成功提取的候选也通过同一逻辑保存元数据。
- 历史记录仅在原错误明确记载有效的“实际页数不足最低要求”时，只读补齐缺失的页数和 PDF 类型；列表、内容类型统计与 CSV 使用相同展示口径。
- 已有字段保留；缺少 PDF、模糊错误、无效页数和无法确认的文档类型不会被补造。历史记录未保存的 PDF 地址、非空页数和文件大小仍保持为空。
- 20 页门槛和已有网页长文 fallback 行为保持不变。

验证：

- 59 项相关后端测试通过，覆盖文档校验错误元数据、20 页边界、网页 fallback、候选跳过保存、历史只读展示、CSV 和类型统计。
- Ruff 检查与相关文件 `git diff --check` 通过。
- CFR run 737：短 PDF 表格显示 14 页 / PDF，内容类型统计为未知 5 条、PDF 1 条。
- CSIS run 741：两条短 PDF 显示 11 页、15 页 / PDF，内容类型统计为未知 2 条、PDF 2 条。
- Atlantic Council run 735：短 PDF 显示 10 页 / PDF，内容类型统计为未知 7 条、PDF 1 条。
- 三个批次的五张候选卡片分别为 `6/0/0/1/5`、`4/0/0/2/2`、`8/0/4/1/3`；逐个点击后，筛选数量、表格行数和空状态均正确。
- 三个批次的 CSV 导出页数与类型和页面一致；桌面截图检查通过，浏览器未发现错误。
- 已只读核对候选 2484、2591、2617、2620 的数据库原值，`page_count` 和 `content_kind` 仍为空，确认历史展示补齐没有改写这些记录。
- 本轮未触发正式采集、报告入库、AI 生成或报告复核状态变更；后续新候选的元数据保存链路通过针对性测试验证。
- 修改前备份、接口核对结果、CSV、页面核对结果及截图保存在 `.codex-backups/short-pdf-metadata-20261002-225006/`。

## 2026-10-02 PIIE run 738 前端候选摘要走查

走查对象：

- PIIE website 来源 `source_id=11`，URL `https://www.piie.com/`。
- 最新网站源运行 `crawl_run_id=738`，运行状态 `success`，耗时 3 秒。

后端统计：

- 候选总数 4 条，新增入库 0 条，4 条均为 `已入库重复`。
- 候选在文档提取前已被去重跳过，未重新获取页数和文档类型；本轮类型统计为未知 4 条，不能据此判定报告无 PDF。

前端实际页面走查：

- 精确打开 PIIE website 最新运行，通过候选网络请求确认 `crawl_run_id=738`。
- 五张摘要卡片显示：全部候选 4、新增入库 0、无 PDF 0、短 PDF 0、已入库重复 4。
- 逐个点击五张卡片，筛选总数、已加载数量及表格数据行数均一致，分别为 4、0、0、0、4。
- 三个 0 条筛选均保留摘要区及筛选控件，显示“当前筛选条件下暂无候选”；新增入库筛选的跳过原因控件按预期禁用。
- 重复筛选中的四条标题与后端记录一致，行内原因为“已入库重复 / 重复候选”。
- 切回全部候选后恢复为 4 行；正常来源提示为“当前无需人工处理，继续观察自动抓取结果”。
- 点击来源“需处理”筛选后，按钮数量与实际列表均为 48，PIIE 网站源不在该列表中；切回全部来源后正常提示仍正确。
- 桌面重复列表及空状态截图检查通过，浏览器控制台和网络未发现错误。

判断与记录：

- PIIE 本轮重复跳过和前端筛选展示通过验收，未发现需要修改的代码问题。
- 继续保持 `pilot_crawl` + `pdf_20_page_required`，每次最多新增 1 篇并人工复核。
- 本轮只进行接口读取和页面走查，未触发采集、AI 生成或报告复核状态变更。
- 文档修改前备份、接口数据、逐卡片核对记录、需处理筛选记录及截图保存在 `.codex-backups/piie-run738-walkthrough-20261002-231149/`。

## 2026-10-02 Brookings / Carnegie 前端候选摘要走查

走查对象：

- Brookings website 来源 `source_id=1`，URL `https://www.brookings.edu/`，最新运行 `crawl_run_id=743`，状态 `success`，耗时 2 秒。
- Carnegie website 来源 `source_id=8`，URL `https://carnegieendowment.org/`，最新运行 `crawl_run_id=745`，状态 `success`，耗时 3 秒。
- Brookings 本轮 3 条候选、Carnegie 本轮 1 条候选，均在文档提取前因已入库重复跳过；未知页数和文档类型不能据此解释为无 PDF。

前端实际页面走查：

- 分别精确打开两个网站源，通过候选请求确认运行编号，未误选 RSS 来源。
- 五张卡片按“全部候选、新增入库、无 PDF、短 PDF、已入库重复”顺序分别为 Brookings 3、0、0、0、3，Carnegie 1、0、0、0、1。
- 逐卡片点击后，选中卡片、筛选控件、筛选总数、已加载数量和候选表格行数均一致。
- 三个 0 条筛选均保留五张卡片及筛选控件，并显示空结果提示；新增入库筛选的跳过原因控件按预期禁用。
- 重复候选标题与后端记录一致，行内原因为“已入库重复 / 重复候选”；切回全部候选后分别恢复 3 行和 1 行。
- 两个网站源均显示“当前无需人工处理，继续观察自动抓取结果”，不出现在“需处理”列表中。
- “需处理”按钮数量与实际列表均为 48；失败的 Brookings RSS 和 RAND RSS 仍保留在列表中，并提示最近抓取失败。
- 1440 x 1000 桌面截图中的长标题换行、重复列表和空状态检查通过，浏览器控制台及网络未发现错误。

判断与记录：

- 两个网站源的候选摘要筛选、空状态和来源处理提示通过验收，本步未发现需要修改的业务代码问题。
- 继续保持 `pilot_crawl` + `pdf_20_page_required`，每次最多新增 1 篇并人工复核。
- 本步只进行接口读取、页面走查和文档更新，未触发新采集、AI 生成、数据库写入或报告复核状态变更。
- 修改前备份、接口结果、逐卡片核对记录、需处理筛选记录及截图保存在 `.codex-backups/brookings-carnegie-walkthrough-20261002-232510/`。

## 2026-10-02 美国重点网站源页面验收汇总

本轮最新网站批次的候选统计：

| 网站来源 | source_id | crawl_run_id | 全部候选 | 新增入库 | 无 PDF | 短 PDF | 已入库重复 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Brookings | 1 | 743 | 3 | 0 | 0 | 0 | 3 |
| Carnegie | 8 | 745 | 1 | 0 | 0 | 0 | 1 |
| CFR | 3 | 737 | 6 | 0 | 0 | 1 | 5 |
| CSIS | 5 | 741 | 4 | 0 | 0 | 2 | 2 |
| PIIE | 11 | 738 | 4 | 0 | 0 | 0 | 4 |
| RAND | 7 | 744 | 9 | 0 | 2 | 0 | 7 |
| Atlantic Council | 9 | 735 | 8 | 0 | 4 | 1 | 3 |
| 合计 | - | - | 35 | 0 | 6 | 4 | 25 |

已验证：

- 七个网站源的五张摘要卡片、筛选数量与表格行数一致，0 条筛选仍可切回其他卡片。
- 正常重复与短 PDF 批次的“需处理：正常”误提示已修复；包含无 PDF 或其他未解释原因的批次仍保留人工处理提示。
- 短 PDF 元数据保留和历史展示补齐已通过验证：CFR 14 页、CSIS 11 / 15 页、Atlantic Council 10 页均正确展示为 PDF，历史数据库原值未被回写。
- 汇总数据在本步末尾通过接口再次核对，证据保存为上述目录中的 `acceptance-summary.json`。

验收边界与遗留事项：

- 本轮结论仅覆盖七个网站源的桌面候选展示和筛选，不等同于整个平台端到端验收；AEI、ECFR 和移动端未纳入这一轮七源走查。
- 七个批次新增入库均为 0，尚未通过本轮批次验证非空“新增入库”列表及“新报告入库 -> 通知”链路，应在后续获准的受控新增样本中补验。
- 前端验收时 Brookings RSS `source_id=52` 仍 active，最新失败运行 `740`：`https://www.brookings.edu/feed/` 返回 HTML，RSS 解析失败；后续已按用户确认停用。
- 前端验收时 RAND RSS `source_id=54` 仍 active，最新失败运行 `746`：`https://www.rand.org/rss.xml` 返回 HTTP 404；后续已按用户确认停用。
- 后续只读核验已完成：Brookings `/feed/` 302 跳转首页；RAND `/rss.xml` 404，官方 China Atom feed 两次均无条目。用户确认后仅停用了旧 RSS，未修改地址或来源准入策略，详见后续两节。

## 2026-10-02 Brookings / RAND RSS 入口只读核验

- 完整方法、官方入口依据和原始响应记录见 [rss-entry-audit-20261002.md](rss-entry-audit-20261002.md)。
- Brookings RSS `source_id=52` 的实际 GET 为 `302 -> / -> 200 HTML`，项目 parser 正确拒绝；官网 HTML 的 RSS 声明不能证明这个入口可用。
- Brookings 官方旧文中的 PlanetPolicy feed 在本环境存在证书主机名不匹配，且栏目不是涉华报告，未作为替代接入。
- RAND RSS `source_id=54` 的实际响应仍为 404；官方中国专题页明确链接的 `https://www.rand.org/topics/china.xml` 虽为有效 Atom，但两次请求均为 0 条，标准 XML 检查与现有 parser 结果一致。
- 现有 RSS parser 5 项测试通过，未发现本次失败是解析器造成的证据；四个来源的前后完整健康快照一致。
- 本步未修改业务代码、来源 URL、启停状态或数据库；网站来源 `1`、`7` 继续 active，机构保持 `pilot_crawl` + `pdf_20_page_required`。
- 只读核验阶段建议停用失效 RSS `52`、`54`，保留网站源及历史记录；后续已获用户确认并执行，详见下一节。未将空 Atom feed 直接替换为 active 入口；网站覆盖率和 1440 分钟抓取间隔仍需另行评估，不能将停用失败 RSS 视为已达到实时监测。
- 修改前备份、临时核验脚本及结果保存在 `.codex-backups/rss-readonly-audit-20261002-234017/`。

## 2026-10-02 Brookings / RAND 失效 RSS 停用

- 用户确认后，通过管理接口仅将 RSS `source_id=52`、`54` 设为 `is_active=false`，保留原 URL、频率、历史错误和全部运行记录；无删除、替换入口或新采集。
- 网站源 `source_id=1`、`7` 保持 active；机构继续 `pilot_crawl` + `pdf_20_page_required`，其余来源配置与全部报告数未变。
- 来源总数仍为 56，active 54 -> 52，停用 2 -> 4，失败 36 -> 34；设置页“需处理”按钮和实际列表均由 48 降至 46。
- 实际页面中两条 RSS 显示停用、重试按钮禁用，历史记录可查看，搜索和恢复全部来源正常；浏览器未发现错误。
- 停用验收时发现既有文案问题：停用来源仍显示“继续观察自动抓取结果”和机构试运行建议；后续已按用户确认统一提示，详见下一节。
- 修改前配置、完整抓取历史、文档备份、API 前后核对及桌面截图保存在 `.codex-backups/rss-disable-20261002-235214/`，详情见 [rss-entry-audit-20261002.md](rss-entry-audit-20261002.md)。

## 2026-10-03 停用来源提示统一

- 来源列表按 `is_active` 展示独立停用提示，采用灰色样式，明确后续自动抓取暂停、历史记录保留。
- 停用来源不再显示自动抓取或试运行建议；准入信息明确标记为“机构准入”，错误与频率标明属于停用前记录。
- 四个停用来源 `52`、`53`、`54`、`55` 及正常网站源 `1`、`7` 的实际页面核验通过；重试禁用与历史查看功能保持正常。
- 停用 CSIS 来源 `55` 的历史运行 `570` 可打开 5 条候选；当前“需处理”按钮与列表同为 45 条，无停用来源混入。本次来源健康接口前后快照一致，未变更配置或筛选规则。
- 类型检查、lint、桌面与窄屏截图检查通过，未发现浏览器错误；本步仅修改前端展示及操作文档。
- 文件备份、API 快照、页面核对记录及截图保存在 `.codex-backups/disabled-source-copy-20261003-191556/`。

## 2026-10-01 Carnegie PDF 识别修复与只读复核

背景：

- Carnegie 属于 P0 美国核心来源，但此前只召回无 PDF 网页，未能满足 `pdf_20_page_required`。
- 当前官网报告页存在 `Full Text (PDF)` 链接，但 PDF 提取器未将 `full text` 识别为报告下载意图。

处理：

- `extract_report_pdf_url` 已将 `full text` 纳入明确报告 PDF 意图，但仍要求目标链接本身是 PDF。
- 新增测试覆盖 Carnegie `Full Text (PDF)` 链接，并确认非 PDF 的 `Full Text` 链接不会被误判。

只读复核：

- 执行 `poetry run python -m app.scripts.audit_source_documents --keys carnegie --max-candidates 5 --discovery-timeout 90 --document-timeout 120`。
- 本轮发现 1 条原始候选、1 条去重候选，抽查 1 条文档通过。
- 样本 `Untangling the Nuclear Knot: A Constructive Agenda for Managing China's Nuclear Relations with the United States and Its Allies` 识别为 PDF，39 页，非空页 38 页，正文约 117,144 字符。

判断：

- Carnegie PDF 提取链路已修复，当前样本符合 20 页 PDF 门槛。
- Carnegie 仍保持 `standard_review`，不直接升级。
- 后续已完成一次受控试写、AI 生成和人工复核通过，升级仍需单独确认。

## 2026-10-01 Carnegie 受控试写

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.pilot_crawl_sources --keys carnegie --allow-standard-review --max-saved 1 --max-candidates 5 --ai-status skipped
```

运行结果：

- `crawl_run_id=726`，`source_id=8`。
- 检查候选 1 条，新增入库 1 条。
- 新增 `report_id=440`：`Untangling the Nuclear Knot: A Constructive Agenda for Managing China's Nuclear Relations with the United States and Its Allies`。
- 文档形态为 PDF，39 页，非空页 38 页，PDF 大小约 748,479 字节，正文约 117,144 字符。
- 新增报告入库时为 `crawl_status=success`、`ai_status=skipped`、`review_status=pending_review`。

内容抽查：

- 标题无替换乱码，正文无替换乱码。
- 正文开头包含封面、标题、作者、目录；结尾包含注释与参考文献信息。
- 正文中 `China` 约 250 次，`nuclear` 约 404 次，主题相关性强。

AI 与人工复核：

- 已对 report 440 触发 AI 生成，48 个分块全部完成，失败 0 个。
- 生成全文翻译约 39,734 字符，主要观点约 1,577 字符，深层研判约 2,347 字符。
- 主要观点包含 4 个分论点，深层研判包含 5 个分论点，导出 Markdown 和 Word 检查通过。
- report 440 已标记为 `approved`，复核事件 id 49；复核意见记录参考文献、URL 和机构地址保留英文较多，可后续人工润色，但不影响本轮自动化流程验收。

判断：

- Carnegie 受控试写成功，PDF 提取和正文抽取链路可用。
- Carnegie 已完成“只读复核 -> 受控试写 -> AI 生成 -> 人工通过”的完整闭环。
- 代码 rollout 已升级为 `pilot_crawl`，文档策略保持 `pdf_20_page_required`。
- 升级后仍保持每次最多新增 1 篇和前端人工复核，不扩大抓取规模。

## 2026-10-01 Carnegie 正式 pilot_crawl 试抓

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.pilot_crawl_sources --keys carnegie --max-saved 1 --max-candidates 5 --ai-status skipped
```

运行结果：

- `crawl_run_id=727`，`source_id=8`。
- 未使用 `--allow-standard-review`，说明 Carnegie 已能通过 `pilot_crawl` 策略守卫。
- 本轮发现候选 1 条，新增入库 0 条。
- 唯一候选为 report 440 对应报告，已被正确标记为 `duplicate_existing`。

判断：

- Carnegie 升级后的正式试抓链路有效，未出现误放行、解析失败或重复入库。
- 后续 Carnegie 可纳入常规小批量试运行，但仍建议保持每次最多新增 1 篇，并继续人工复核新增样本。

## 2026-10-01 Atlantic Council website 解析器修复与只读复核

背景：

- Atlantic Council 属于 P1 美国扩展重点来源。
- 2026-09-27 审计时，website 来源缺少专用解析器，主审计停在 `discovery_error`。
- RSS 虽可返回大量候选，但包含新闻、博客、活动、快评和转载信息，噪声明显高于报告入口。

处理：

- 已将 Atlantic Council 接入 `CoreSiteConfig` 通用解析器。
- 发现入口限定为中国专题页、in-depth research reports 和 strategy paper series。
- URL 路径限定为 `/in-depth-research-reports/report/`、`/in-depth-research-reports/issue-brief/` 和 `/content-series/atlantic-council-strategy-paper-series/`。
- 新增测试覆盖中国专题页报告卡片解析，以及普通报告列表中无涉华信号候选的过滤。

只读复核：

- 执行 `poetry run python -m app.scripts.audit_source_documents --keys atlantic_council --max-candidates 5 --discovery-timeout 90 --document-timeout 120`。
- 本轮发现 2 条原始候选、2 条去重候选，抽查 2 条。
- 通过 1 条 PDF 报告：`Building a multilateral cognitive warfare defense network: A collaborative framework for the United States, Japan, and Taiwan`，PDF 24 页，非空页 24 页，正文约 76,376 字符。
- 失败 1 条：`Technology and the Global South: A US strategy for competitiveness`，页面为网页长报告，当前页面未发现 PDF 链接，按 `pdf_20_page_required` 被拒绝。

判断：

- Atlantic Council website 解析器已修复，候选发现不再报错。
- 当前 PDF 文档提取链路已有 20 页以上合格样本，后续已完成一次受控试写。
- Atlantic Council 仍保持 `standard_review`，暂不升级。
- 是否允许无 PDF 的网页长报告作为 `web_article` 入库需单独确认；未确认前继续保持 `pdf_20_page_required`。

## 2026-10-01 Atlantic Council 受控试写

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.pilot_crawl_sources --keys atlantic_council --allow-standard-review --max-saved 1 --max-candidates 5 --ai-status skipped
```

运行结果：

- `crawl_run_id=728`，`source_id=9`。
- 检查候选 2 条，新增入库 1 条。
- 新增 `report_id=441`：`Building a multilateral cognitive warfare defense network: A collaborative framework for the United States, Japan, and Taiwan`。
- 文档形态为 PDF，24 页，非空页 24 页，PDF 大小约 4,159,506 字节，正文约 76,376 字符。
- 新增报告入库时为 `crawl_status=success`、`ai_status=skipped`、`review_status=pending_review`。
- 另一候选 `Technology and the Global South: A US strategy for competitiveness` 因页面未发现 PDF 链接被跳过。

内容抽查：

- 正文无替换乱码。
- 正文中 `China` 约 68 次，`Chinese` 约 29 次，`Taiwan` 约 143 次，`Japan` 约 126 次，`cognitive` 约 75 次，主题相关性较强。

AI 生成：

- 已对 report 441 触发 AI 生成，31 个分块全部完成，失败 0 个。
- 生成全文翻译约 28,128 字符，主要观点约 1,614 字符，深层研判约 2,196 字符。
- 主要观点包含 4 个分论点，深层研判包含 5 个分论点，导出 Markdown 和 Word 检查通过。
- report 441 已标记为 `approved`，复核事件 id 50；复核意见记录报告主题涉中美日台认知战防御网络，涉华相关性明确，翻译术语后续可人工润色但不影响本轮自动化流程验收。

判断：

- Atlantic Council 受控试写成功，PDF 提取和正文抽取链路可用。
- Atlantic Council 已完成“解析器修复 -> 只读复核 -> 受控试写 -> AI 生成 -> 人工通过”的完整闭环。
- Atlantic Council 仍保持 `standard_review`，暂不升级。
- 第二次受控试写已执行但无新增，说明当前发现入口下可保存 PDF 样本不足，暂不建议直接升级为 `pilot_crawl`。
- 是否允许无 PDF 的网页长报告作为 `web_article` 入库仍需单独确认。

## 2026-10-01 Atlantic Council 第二次受控试写

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.pilot_crawl_sources --keys atlantic_council --allow-standard-review --max-saved 1 --max-candidates 10 --ai-status skipped
```

运行结果：

- `crawl_run_id=729`，`source_id=9`。
- 检查候选 2 条，新增入库 0 条。
- report 441 对应 PDF 报告被正确标记为 `duplicate_existing`。
- `Technology and the Global South: A US strategy for competitiveness` 仍因页面未发现 PDF 链接被跳过。
- 试写前后 `source_id=9` 报告清单均只有 report 441，未发生误入库。

判断：

- Atlantic Council 第二次受控试写验证了去重和 PDF 门槛仍按预期生效。
- 当前解析入口下不足以产生第二篇可保存 PDF 样本。
- 下一步应优先二选一：扩展 Atlantic Council PDF 报告发现入口，或单独确认是否允许无 PDF 的网页长报告按 `web_article` 入库。

## 2026-10-01 Atlantic Council PDF 发现入口扩展

处理：

- 新增 `Global China Hub publications` 入口。
- 新增 `content-type/in-depth-research-reports` 入口及已验证能产生涉华 PDF 样本的分页。
- Atlantic Council 候选改为要求标题或 URL 自身具备 China / Chinese / Taiwan / East Asia / Northeast Asia 等涉华或周边地区信号，避免只因列表页上下文混入无关 PDF。

只读复核：

- 执行 `poetry run python -m app.scripts.audit_source_documents --keys atlantic_council --max-candidates 10 --discovery-timeout 120 --document-timeout 150`。
- 本轮发现 8 条原始候选、8 条去重候选，抽查 8 条。
- 文档通过 3 条，失败 5 条。
- 通过样本包括：
  - 已入库 report 441 对应 PDF，24 页，正文约 76,376 字符；
  - `Preparing for and countering limited nuclear attacks in East Asia: Guardian Tiger III`，PDF 44 页，正文约 141,021 字符；
  - `Balancing openness and control: Cross-border health data and AI governance in China`，PDF 38 页，正文约 178,890 字符。
- 严格过滤后不再保留标题和 URL 均无涉华/周边信号的 `Financing the end of the digital divide`。

判断：

- 扩展后的发现入口已经能提供第二篇和第三篇可保存 PDF 样本。
- Atlantic Council 仍保持 `standard_review`，暂不升级。
- 后续已执行一次扩展入口后的受控试写，新增 report 442。
- 是否允许无 PDF 的网页长报告作为 `web_article` 入库仍需单独确认。

## 2026-10-01 Atlantic Council 扩展入口后受控试写

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.pilot_crawl_sources --keys atlantic_council --allow-standard-review --max-saved 1 --max-candidates 10 --ai-status skipped
```

运行结果：

- `crawl_run_id=730`，`source_id=9`。
- 检查候选 8 条，新增入库 1 条。
- 新增 `report_id=442`：`Balancing openness and control: Cross-border health data and AI governance in China`。
- 文档形态为 PDF，38 页，非空页 38 页，PDF 大小约 639,509 字节，正文约 178,890 字符。
- 新增报告入库时为 `crawl_status=success`、`ai_status=skipped`、`review_status=pending_review`。
- report 441 已入库重复；`Guardian Tiger III` 已作为历史 report 344 存在并被正确去重；3 条候选因无 PDF 或页数不足被跳过。

内容抽查：

- 正文无替换乱码。
- 正文中 `China` 约 432 次，`Chinese` 约 56 次，`AI` / `artificial intelligence` 约 171 次，`data` 约 763 次，`health` 约 256 次，主题相关性强。

判断：

- 扩展入口后的受控试写成功，新增样本符合 20 页 PDF 门槛。
- Atlantic Council 仍保持 `standard_review`，暂不升级。
- 后续已按用户授权触发 report 442 AI 生成并完成前端复核，已标记为 `approved`。

## 2026-10-01 Atlantic Council report 442 AI 生成

执行说明：

- 已获得用户明确授权：将 report 442 全文发送给当前后端配置的 LLM 服务进行 AI 生成。
- 生成前已备份 report 442 数据库快照和相关文档到 `.codex-backups/step23-report442-ai-20261001-190000/`。
- 采用项目现有分块链路：`prepare_report_ai_chunks` -> `run_report_ai_chunk` -> `run_report_ai_finalization`。

运行结果：

- report 442 共生成 73 个 AI 分块，最终 73 个分块全部成功。
- 普通分块重试中 `chunk_id=3491` 曾因译文长度不足失败；该块为正文加脚注，后续使用同一 LLM 服务按“逐段完整翻译并保留脚注、链接”的严格提示恢复成功，恢复译文约 1,511 字符。
- 整篇 finalizer 成功，生成后为 `ai_status=success`、`review_status=pending_review`。
- 生成全文翻译约 70,107 字符，主要观点约 1,697 字符，深层研判约 2,088 字符。
- 主要观点包含 4 个分论点，深层研判包含 5 个分论点，符合当前交付口径。
- 已导出 Markdown、Word 和质量检查文件到 `.codex-backups/step23-report442-ai-20261001-190000/`。

判断：

- 后续已完成前端复核并标记为 `approved`，详见下一节。

## 2026-10-01 Atlantic Council report 442 前端复核通过

复核结果：

- 前端报告页 `/reports?report_id=442` 可访问，详情接口、列表检索、AI 进度、Markdown 导出和 Word 导出检查通过。
- PDF 元数据合格：38 页，38 个非空页，PDF 链接为 Atlantic Council 官方 PDF。
- 正文长度约 178,890 字符，AI 分块 73 个全部成功，失败 0 个。
- 交付物检查通过：全文翻译约 70,107 字符；主要观点约 1,697 字符、4 个分论点；深层研判约 2,088 字符、5 个分论点。
- 已将 report 442 标记为 `approved`，复核事件 id 51。
- 复核意见记录：报告详情接口、报告列表检索、PDF 元数据、正文完整性、AI 翻译稿、主要观点、深层研判及 Markdown/Word 导出均已检查；后续仍建议人工细读术语和脚注翻译。

判断：

- report 442 已完成“扩展入口 -> 受控试写 -> AI 生成 -> 前端复核通过”的完整闭环。
- 后续已按用户确认将 Atlantic Council 升级为 `pilot_crawl`，详见下一节。

## 2026-10-01 Atlantic Council 升级为 pilot_crawl

处理：

- 已将 `atlantic_council` 加入 `PILOT_CRAWL_KEYS`。
- 文档策略继续保持 `pdf_20_page_required`，不放开无 PDF 网页长报告入库。
- 仍坚持每次最多新增 1 篇、AI 成功后前端人工复核，不扩大抓取规模。

升级依据：

- report 441 已完成“解析器修复 -> 只读复核 -> 受控试写 -> AI 生成 -> 前端复核通过”的完整闭环。
- report 442 已完成“扩展入口 -> 受控试写 -> AI 生成 -> 前端复核通过”的完整闭环。
- 扩展后的 PDF 发现入口能提供 20 页以上、主题显性涉华或周边地区相关的长报告样本。

判断：

- Atlantic Council 已满足进入保守 `pilot_crawl` 的最低样本闭环要求。
- 升级后仍应重点观察重复入库、PDF 获取失败、短 PDF 跳过和无 PDF 网页报告跳过情况。

## 2026-10-01 Atlantic Council 正式 pilot_crawl 试抓

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.pilot_crawl_sources --keys atlantic_council --max-saved 1 --max-candidates 10 --ai-status skipped
```

运行结果：

- `crawl_run_id=733`，`source_id=9`。
- 未使用 `--allow-standard-review`，说明 Atlantic Council 已能通过 `pilot_crawl` 策略守卫。
- 本轮发现候选 8 条，新增入库 0 条。
- 3 条候选被标记为已入库重复，包括 report 441、report 442 和历史 report 344 对应报告。
- 5 条候选因页面未发现 PDF 或 PDF 低于 20 页门槛被跳过。

判断：

- Atlantic Council 升级后的正式试抓链路有效，未出现误放行、解析失败或重复入库。
- 本轮没有新增报告并非异常，而是去重和 PDF 门槛按预期生效。
- 后续 Atlantic Council 可纳入常规小批量试运行，但仍建议保持每次最多新增 1 篇，并继续人工复核新增样本。

## 2026-10-01 Atlantic Council report 344 前端复核通过

复核对象：

- report 344：`Preparing for and countering limited nuclear attacks in East Asia: Guardian Tiger III`。
- 该报告在扩展入口只读复核中被再次发现，但已作为历史报告入库，因此正式试抓时按重复跳过。

复核结果：

- 前端报告页 `/reports?report_id=344` 可访问，详情接口、列表检索、AI 进度、Markdown 导出和 Word 导出检查通过。
- PDF 元数据合格：44 页，44 个非空页，PDF 链接为 Atlantic Council 官方 PDF。
- 正文长度约 141,021 字符，AI 分块 38 个全部成功，失败 0 个。
- 交付物检查通过：全文翻译约 54,002 字符；主要观点约 1,688 字符、4 个分论点；深层研判约 2,070 字符、4 个分论点。
- 已将 report 344 标记为 `approved`，复核事件 id 52。
- 复核意见记录：报告主题为东亚有限核攻击准备与应对，涉及中国、朝鲜半岛、日本、美国延伸威慑等区域安全议题，可纳入涉华及周边安全研究库。

判断：

- report 344 已完成历史样本补复核，Atlantic Council 当前已通过复核的样本扩展至 report 344、441、442。
- 后续 Atlantic Council 仍保持 `pilot_crawl` + `pdf_20_page_required`，每次最多新增 1 篇并人工复核。

## 2026-10-01 Atlantic Council 无 PDF 候选发现阶段预检

本轮处理：

- 为 Atlantic Council website 发现链路增加详情页 PDF 链接预检。
- 预检确认无 PDF 的候选直接在候选明细中标记为 `未发现 PDF 链接`，错误摘要为 `发现阶段预检：报告详情页中未发现 PDF 链接。`
- 预检发现 PDF 的候选会保留 `pdf_url`，随后仍由正式文档检查执行 PDF 下载、正文抽取和 20 页门槛。

验证：

```powershell
cd backend
poetry run python -m app.scripts.pilot_crawl_sources --keys atlantic_council --max-saved 1 --max-candidates 8 --ai-status skipped
```

结果：

- `crawl_run_id=735`，`source_id=9`。
- 发现候选 8 条，新增入库 0 条。
- 已入库重复 3 条。
- 发现阶段预检确认无 PDF 4 条。
- 正式文档检查识别短 PDF 1 条：`chinese-mining-in-west-africa.pdf` 为 10 页，低于 20 页门槛。

判断：

- Atlantic Council 的无 PDF 页面不再进入后续 PDF 下载/抽取失败链路，减少候选失败噪声。
- 候选展示仍保留所有跳过记录，便于老师区分“无 PDF”“短 PDF”和“重复入库”。
- 文档策略继续保持 `pdf_20_page_required`，不放开无 PDF 网页长文入库。

## 2026-09-21 AEI 阶段收尾

- AEI 已从 `discovery_only` 升级为 `pilot_crawl`，但仍保持 `web_article_allowed` 的来源特例和每次最多新增 1 篇的保守试运行节奏。
- 现有 8 篇 AEI 入库样本均已完成前端人工复核并通过。
- 报告 356 原始 AEI 页面为导流/转载页，已切换到 Asia Society 原始全文页，正文从 6,666 字符提升到 84,076 字符，并完成 AI 重生成与复核批准。
- AEI 后续重点不是继续放宽门槛，而是观察网页长文稳定性、重复入库率、候选跳过原因和通知噪声。

## 2026-09-21 美国重点来源阶段验收

- Brookings、CFR、CSIS、PIIE、AEI 已完成历史待复核样本清理，并进入保守小批量试运行。
- P0 历史 `pending_review` 样本已清零；CSIS RSS 旧活动页样本已标记为 `rejected`，RSS 来源 `source_id=53` 已停用。
- CSIS 重复 website 来源 `source_id=55` 已停用，后续只保留 `source_id=5` 的 `/analysis` 主入口。
- 后续不扩大单次抓取规模，仍坚持每次最多新增 1 篇、AI 成功后前端复核。
- 下一阶段可以开始非美国重点来源只读审计，但不得绕过“只读审计 -> 小样本复核 -> pilot_crawl”的准入流程。

## 2026-09-22 ECFR 准入与升级

ECFR 已完成非美国来源中最完整的一轮验证，详细建议见 [ecfr-admission-recommendation-20260922.md](ecfr-admission-recommendation-20260922.md)。

当前证据：

- 解析器可用，只读审计发现 18 条候选，抽查 3 条文档全部通过。
- 已有 2 篇真实样本完成“入库 -> AI 生成 -> 前端复核 -> approved”闭环。
- 报告 `398` 为 PDF，26 页；报告 `420` 为网页长文，正文 43,866 字符。
- ECFR 同时具备 PDF 和长网页报告价值，后续文档策略建议考虑 `web_article_allowed`。

升级处理：

- ECFR `source_id=21` 可保持 active。
- 代码 rollout 已升级为 `pilot_crawl`。
- 文档策略已设为 `web_article_allowed`。
- 常规 crawler 已可通过 rollout guard，但仍应保持每次最多新增 1 篇和前端人工复核。

建议：

- ECFR 可作为欧洲来源首个小批量试运行对象。
- 升级不代表全量自动化；仍需观察短评论混入、重复入库、通知噪声和 AI finalizer 字数边界问题。
- 如后续连续出现网页长文质量波动，应重新收紧 ECFR 的网页长文准入规则。
- 升级后第一次正式试抓 `crawl_run_id=680` 已通过 policy 放行，新增报告 `422`，当前为 `ai_status=skipped`、`review_status=pending_review`，待前端复核正文质量。
