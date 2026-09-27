# 来源准入与试运行状态

更新时间：2026-09-27

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
| `brookings` | Brookings Institution | P0 | `pilot_crawl` | `pdf_20_page_required` | 允许 | 10 篇历史样本已全部复核通过；继续每次最多新增 1 篇 |
| `cfr` | Council on Foreign Relations | P0 | `pilot_crawl` | `pdf_20_page_required` | 允许 | 5 篇历史 PDF 样本已全部复核通过；继续每次最多新增 1 篇 |
| `csis` | Center for Strategic and International Studies | P0 | `pilot_crawl` | `pdf_20_page_required` | 允许 | 主入口 4 篇 PDF 样本已复核通过；RSS 旧活动页已拒绝并停用；继续每次最多新增 1 篇 |
| `piie` | Peterson Institute for International Economics | P0 | `pilot_crawl` | `pdf_20_page_required` | 允许 | 4 篇历史 PDF 样本已全部复核通过；继续每次最多新增 1 篇 |
| `aei` | American Enterprise Institute | P1 | `pilot_crawl` | `web_article_allowed` | 允许 | 8 篇入库样本已全部复核通过；356 已补抓 Asia Society 原始全文并重跑 AI；继续每次最多新增 1 篇并人工复核 |
| `ecfr` | European Council on Foreign Relations | P2 | `pilot_crawl` | `web_article_allowed` | 允许 | 3 篇受控样本已全部复核通过，覆盖 PDF 和网页长文；继续每次最多新增 1 篇并人工复核 |
| `cap` | Center for American Progress | P1 | `blocked` | `source_access_blocked` | 不允许 | 需先确认稳定入口或可授权访问方式 |
| `cato` | Cato Institute | P1 | `blocked` | `source_access_blocked` | 不允许 | 普通 HTTP 抓取受站点防护影响，暂缓自动化 |
| `heritage` | The Heritage Foundation | P1 | `blocked` | `source_access_blocked` | 不允许 | 需先确认稳定入口、官方 feed 或人工维护入口 |
| 其他来源 | - | P0-P4 | `standard_review` | `pdf_20_page_required` | 不允许 | 进入入库前必须先完成只读审计和人工确认 |

## 老师重点名单中的待审计来源

以下来源来自老师附件，属于优先接入规划，但尚不代表当前代码已配置专用解析器或已允许自动入库。接入前仍需按 [source-onboarding-playbook.md](source-onboarding-playbook.md) 完成入口确认、只读审计、小样本复核和 rollout 策略更新。

| 建议 key | 来源 | 机构层级 | 规划状态 | 建议文档策略 | 自动入库试运行 | 下一步处理 |
| --- | --- | --- | --- | --- | --- | --- |
| `rand` | RAND Corporation | P0 | `standard_review` | `pdf_20_page_required` | 不允许 | 已收紧标题/URL 涉华过滤；修复后只读复审通过，可第二次受控试写，暂不升级 |
| `carnegie` | Carnegie Endowment for International Peace | P0 | `standard_review` | `pdf_20_page_required` | 不允许 | 当前只召回无 PDF 网页；需修正文档提取或确认是否允许网页长文 |
| `atlantic_council` | Atlantic Council | P1 | `standard_review` | `pdf_20_page_required` | 不允许 | website 缺专用解析器，RSS 噪声高；需先补报告页解析与过滤 |
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
