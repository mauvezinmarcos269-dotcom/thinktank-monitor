# P0/P1 来源运行阶段报告

更新时间：2026-09-22

本文面向“老师决策查看”和“后续开发执行”两类场景，汇总当前美国重点智库来源的接入、入库、复核和风险状态。详细审计过程见 [source-onboarding-audit-20260915.md](source-onboarding-audit-20260915.md)，准入口径见 [source-rollout-status.md](source-rollout-status.md)。

## 一、阶段结论

当前平台已经形成一条可复用的来源接入闭环：

1. 先做候选发现和只读审计，不直接入库。
2. 对候选正文质量、PDF 页数、涉华相关性和重复率做小样本检查。
3. 通过后进入 `pilot_crawl`，每次最多新增 1 篇，降低误入库和通知噪声。
4. 入库后生成全文翻译稿、主要观点和深层研判，再由前端人工复核。
5. 复核通过后标记为 `approved`，问题样本保持 `pending_review` 或进入重跑/补抓流程。

截至 2026-09-21，P0/P1 美国重点来源中：

- Brookings、CFR、CSIS、PIIE、AEI 已进入 `pilot_crawl` 小批量试运行。
- CSIS 和 AEI 已完成明确的“抓取 -> AI 生成 -> 前端复核 -> 批准”闭环样本。
- CAP、Cato、Heritage 暂不建议进入自动入库，主要原因是入口稳定性、站点防护或官方入口仍需确认。
- Brookings、CFR、PIIE 已具备试运行入口，但历史入库样本仍需集中做前端复核。

## 二、来源状态总览

| key | 来源 | 层级 | 当前状态 | 文档策略 | 当前结论 |
| --- | --- | --- | --- | --- | --- |
| `brookings` | Brookings Institution | P0 | `pilot_crawl` | `pdf_20_page_required` | 可小批量试运行；10 篇历史待复核样本已全部 `approved` |
| `cfr` | Council on Foreign Relations | P0 | `pilot_crawl` | `pdf_20_page_required` | 可小批量试运行；5 篇历史待复核 PDF 样本已全部 `approved` |
| `csis` | Center for Strategic and International Studies | P0 | `pilot_crawl` | `pdf_20_page_required` | 主入口已有 4 篇 `approved` 样本；重复 website 和 RSS 旧活动页来源均已停用 |
| `piie` | Peterson Institute for International Economics | P0 | `pilot_crawl` | `pdf_20_page_required` | 可小批量试运行；4 篇历史待复核 PDF 样本已全部 `approved` |
| `aei` | American Enterprise Institute | P1 | `pilot_crawl` | `web_article_allowed` | 8 篇入库样本均已 `approved`；继续每次最多新增 1 篇并人工复核 |
| `cap` | Center for American Progress | P1 | `blocked` | `source_access_blocked` | 暂不自动入库；需确认稳定入口或授权访问方式 |
| `cato` | Cato Institute | P1 | `blocked` | `source_access_blocked` | 普通 HTTP 抓取受站点防护影响；暂缓自动化 |
| `heritage` | The Heritage Foundation | P1 | `blocked` | `source_access_blocked` | 暂不自动入库；已有历史待复核样本不代表来源可放开 |

## 三、已验证闭环

### CSIS

CSIS 已完成 sitemap 召回增强、PDF 入库、AI 生成和前端复核闭环。当前保留 `source_id=5` 的 `https://www.csis.org/analysis` 作为主入口，停用重复来源 `source_id=55` 和旧活动页 RSS 来源 `source_id=53`。正式试抓 `crawl_run_id=621` 发现 5 条候选，未新增入库，主要原因为重复和短 PDF。

当前结论：

- CSIS 可保留 `pilot_crawl`。
- 继续坚持 20 页 PDF 门槛。
- 每次最多新增 1 篇，新增后必须前端复核。
- RSS 来源返回 2016 年旧活动页，不适合作为报告召回入口，已停用。

### AEI

AEI 已从 `discovery_only` 升级为 `pilot_crawl`，但仍属于网页长文特例来源。现有 8 篇入库样本已全部前端复核通过。报告 356 原始 AEI 页面为导流/转载页，已补抓 Asia Society 原始全文，正文从 6,666 字符提升到 84,076 字符，并重新生成 AI 成果后批准。

当前结论：

- AEI 可保留 `pilot_crawl`。
- 网页长文可以作为报告形态，但必须关注转载页、导流页和合作机构原始页。
- 继续每次最多新增 1 篇，新增后必须前端复核。

## 四、历史样本复核进展

### Brookings

2026-09-21 已完成 Brookings 三批共 10 篇历史待复核样本前端确认并批准：

| 报告 ID | 标题 | 复核结果 |
| --- | --- | --- |
| 345 | How secure is Taiwan? The view from Taipei | `approved` |
| 346 | A summer of AI summits reveals a widening US-China divide | `approved` |
| 347 | Europe’s China Shock 2.0: Where does it go from here? | `approved` |
| 348 | Middle power AI agency: Preserving choice between the United States and China | `approved` |
| 349 | Turning the tide: China seeks to set the rules at sea | `approved` |
| 350 | What’s lost when reporters leave China? | `approved` |
| 351 | Why Beijing isn’t taking the bait with Trump | `approved` |
| 352 | The hidden tradeoffs of using Trump’s tariffs as leverage with China | `approved` |
| 353 | Advancing human control of military AI | `approved` |
| 378 | How strong is the Chinese Communist Party’s hold on power? | `approved` |

Brookings 历史待复核样本已清零。后续 Brookings 新增样本仍按每次最多新增 1 篇、前端人工复核的节奏推进。

### CFR

2026-09-21 已完成 CFR 5 篇历史待复核 PDF 样本前端确认并批准：

| 报告 ID | 标题 | 页数 | 复核结果 |
| --- | --- | ---: | --- |
| 365 | Out of Ammo: A Two-Year Sprint to Rebuild the American Arsenal and Deter China | 20 | `approved` |
| 366 | The Pharma Choke Point | 96 | `approved` |
| 367 | Leapfrogging China’s Critical Minerals Dominance | 50 | `approved` |
| 368 | The Next Taiwan Crisis Won’t Be Like the Last | 20 | `approved` |
| 379 | The Cyber Gap | 43 | `approved` |

CFR 历史待复核样本已清零。后续 CFR 新增样本继续保持 PDF 页数门槛和前端人工复核。

### PIIE

2026-09-21 已完成 PIIE 4 篇历史待复核 PDF 样本前端确认并批准：

| 报告 ID | 标题 | 页数 | 复核结果 |
| --- | --- | ---: | --- |
| 370 | China's economic security growth model and implications for the US-China security dilemma | 56 | `approved` |
| 371 | How did Trump’s 2025 trade war affect the decoupling of US-China supply chains? | 37 | `approved` |
| 372 | US-China cooperative interdependence: Opportunities and obstacles | 73 | `approved` |
| 373 | Made with China: Global supply chains and the limits of US decoupling | 45 | `approved` |

PIIE 历史待复核样本已清零。后续 PIIE 新增样本继续保持 PDF 页数门槛和前端人工复核。

### CSIS

2026-09-21 已完成 CSIS 历史待复核样本清理：

| 报告 ID | 来源 | 标题 | 处理结果 |
| --- | --- | --- | --- |
| 343 | 主入口 `/analysis` | The Insurance Industry’s Retreat from AI Threatens to Slow Innovation and Adoption | `approved` |
| 261-270 | RSS `rss.xml` | 2016 年旧活动页和短网页内容 | `rejected` |

CSIS 主入口历史待复核 PDF 样本已批准，RSS 旧活动页样本已拒绝，`source_id=53` 已停用。后续 CSIS 只保留 `/analysis` 主入口参与小批量试运行。

## 五、主要风险

### 1. 准入试运行不等于全量自动化

`pilot_crawl` 只表示来源通过小样本验证，可以小批量写入报告库。当前不建议直接扩大到自动批量抓取，否则容易引入重复报告、短文档、导流页或通知噪声。

### 2. 网页长文需要更严格的出处判断

AEI 356 说明，一些智库页面可能只是转载、摘要或导流页。后续对网页长文要记录原始 URL、正文长度、是否存在 `Continue reading` 等线索，并在必要时补抓原始全文。

### 3. 历史待复核样本会影响老师体验

P0 历史 `pending_review` 样本已于 2026-09-21 完成清理。后续风险转为新增样本质量控制：新增报告仍需坚持小批量、强去重、页数门槛和前端人工复核。

### 4. 阻塞来源不能用机构重要性硬推

CAP、Cato、Heritage 都是重要来源，但当前不适合直接自动入库。应先解决稳定入口、官方 feed、授权 API 或人工维护方式，再进入只读审计。

## 六、阶段验收结论

截至 2026-09-21，P0/P1 美国重点来源已完成阶段验收。验收口径不是“全量自动抓取”，而是“已具备小批量、可追踪、可复核的稳定运行基础”。

| 来源 | 入库策略 | 历史样本处理 | 保留入口 | 停用入口或拒绝样本 | 验收结论 |
| --- | --- | --- | --- | --- | --- |
| Brookings | `pilot_crawl` | 10 篇全部 `approved` | website 主入口 | 无 | 通过 |
| CFR | `pilot_crawl` | 5 篇 PDF 全部 `approved` | website 主入口 | 无 | 通过 |
| CSIS | `pilot_crawl` | 4 篇主入口 PDF `approved`，10 篇 RSS 旧活动页 `rejected` | `source_id=5` `/analysis` | `source_id=53` RSS、`source_id=55` 重复 website | 通过，但仅保留主入口 |
| PIIE | `pilot_crawl` | 4 篇 PDF 全部 `approved` | website 主入口 | 无 | 通过 |
| AEI | `pilot_crawl` + `web_article_allowed` | 8 篇网页长文全部 `approved` | website 主入口 | 无 | 通过，但维持网页长文特例复核 |
| CAP | `blocked` | 未进入自动入库 | 暂无稳定入口 | 自动化暂缓 | 不通过，待入口确认 |
| Cato | `blocked` | 未进入自动入库 | 暂无稳定入口 | 站点防护影响普通抓取 | 不通过，待入口确认 |
| Heritage | `blocked` | 未进入自动入库 | 暂无稳定入口 | 自动化暂缓 | 不通过，待入口确认 |

验收后运行规则：

1. Brookings、CFR、CSIS、PIIE、AEI 继续每次最多新增 1 篇。
2. 新增样本必须保持 AI 成功后前端人工复核，再决定 `approved`、`needs_rerun` 或 `rejected`。
3. PDF 来源继续执行 20 页门槛；AEI 继续允许网页长文，但需检查原始出处和正文长度。
4. CSIS 只保留 `/analysis` 主入口，RSS 和重复 website 不参与后续试运行。
5. 阻塞来源不因机构重要性而绕过准入流程。

## 七、下一步开发优先级

建议下一阶段按以下顺序推进：

1. 对 Brookings、CFR、CSIS、PIIE、AEI 继续维持每次最多新增 1 篇的小批量试运行。
2. 观察新增样本的重复率、跳过原因、通知噪声和前端复核通过率。
3. 非美国/周边来源第一轮只读审计见 [non-us-source-readonly-audit-20260921.md](non-us-source-readonly-audit-20260921.md)；当前主要阻塞点是缺少专用 website 解析器。
4. `chatham_house` 已完成最小解析器试点，但当前首页没有符合“报告型标签 + 涉华信号”的候选，仍保持 `standard_review`。
5. `ecfr` 已完成第二个非美国解析器试点，只读审计发现 18 条候选，抽查 3 条文档全部通过；人工试写阶段因后台常规 crawler 缺少 rollout policy guard，曾误批量入库，现已清理。
6. ECFR 当前仅保留报告 `398` 作为人工试写样本，`ai_status=skipped`、`review_status=pending_review`；来源 `source_id=21` 已临时停用，待前端复核 398 正文质量后再决定是否触发 AI 和是否恢复来源。
7. CAP、Cato、Heritage 暂缓自动化，只维护阻塞原因和可选入口调研记录。

## 八、给老师的简版说明

当前系统已经能对一批美国重点智库进行小批量实时监测，并自动生成全文翻译、主要观点和深层研判。CSIS 和 AEI 已经完成较完整的闭环验证，说明技术路线可行。

但平台还没有进入“完全自动放开”的阶段。下一步重点不是盲目增加来源数量，而是在 P0/P1 美国来源小批量稳定运行的基础上，选择少量非美国重点来源做只读审计，确认入口、报告形态和输出质量后再逐步扩大范围。这样可以保证老师看到的报告不是“抓到了就推送”，而是经过来源准入、内容质量、AI 生成和人工复核的可控成果。
