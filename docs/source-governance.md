# 来源数据治理说明

更新时间：2026-09-27

## 目标

本项目面向全球智库、研究机构和期刊的涉华长篇研究报告监测。来源治理的目标不是尽可能多地堆机构名称，而是确保老师看到的报告来源可靠、重点清楚、可解释、可持续维护。

## 当前原则

1. 美国优先：优先覆盖外交、安全、经贸、科技、产业政策和中美关系相关的美国顶级智库。
2. 重要国家补充：英国、德国、法国、欧盟层面机构作为第二层，重点关注对华政策、印太、安全、经贸和技术治理。
3. 周边国家补充：日本、韩国、东盟相关机构作为第三层，重点关注地区安全、供应链、产业政策和区域经济。
4. 待校对池暂不等同于重点来源：附件 Top 100 中未校对官网、RSS、报告库入口的机构只作为候选名单，不应直接视为稳定监测来源。
5. 国内机构默认后置：除非老师明确要求，本平台第一阶段应聚焦境外涉华研究动向，国内机构可作为对照或补充来源。

## 老师重点名单口径

老师附件中的 `智库机构.docx` 是当前来源建设的第一优先覆盖池，已整理为 [teacher-required-thinktanks-20260927.md](teacher-required-thinktanks-20260927.md)；`think tank top 100.pdf` 作为后续扩展候选池和缺口校准参考。

执行上采用以下口径：

1. Word 名单优先：Brookings、Heritage、CFR、Cato、CSIS、AEI、RAND、Carnegie、Atlantic Council、Hoover、PIIE、Bruegel、Chatham House、Wilson Center、CAP、NBER、CEPR、RIETI、ERIA、ifo、IFRI、JIIA 等机构，优先纳入审计和接入计划。
2. PDF Top 100 校准：Top 100 中尚未覆盖的美国、欧洲、日本、韩国、东盟及中国周边机构，可作为 P4 候选池分批评估。
3. 重复与简称先确认：Peter G. Peterson / IIE 初步按 PIIE 去重；`Leibniz Institute`、`German Institute / Deutsches Institut` 等泛称需先确认完整机构名称、官网和报告入口，再进入正式来源配置。
4. 准入标准不降低：老师重点名单中的机构仍需满足公开入口稳定、报告可下载、篇幅通常不少于 20 页、不是新闻短评或活动稿等条件。

## 报告准入口径

1. 优先收录 PDF 或 PDF 直链报告，PDF 页数一般不少于 20 页。
2. 无 PDF 的研究成果，如果网页正文足够长、具备报告型标题或页面结构，也可作为“网页长文”正式入库。
3. 平台用 `content_kind` 标记正文来源：`pdf` 表示 PDF 报告，`web_article` 表示无 PDF 但正文足够长的网页长文报告。
4. 候选报告仍需经过涉华相关性判断；`direct` 或 `substantial` 均视为涉华并可入库，`incidental` 和 `unrelated` 不入库。
5. 入库不要求标题明确出现 China/Chinese/Beijing/Taiwan 等词。只要正文核心论证、政策建议、战略竞争、产业链、科技治理、地区安全或国际格局分析中实质涉及中国因素，即使标题不明显涉华，也应按 `substantial` 收录。
6. 未通过 PDF/网页正文质量检查、涉华判断或去重检查的候选会保留跳过原因，便于人工复核。

## 分层口径

### P0 美国核心来源

用于最先打磨爬虫、AI 处理和提醒闭环。当前种子数据已包含：

- Brookings Institution
- Center for Strategic and International Studies
- RAND Corporation
- Council on Foreign Relations
- Carnegie Endowment for International Peace
- Peterson Institute for International Economics

### P1 美国扩展来源

用于扩大美国政策圈覆盖面，适合在 P0 稳定后继续补解析器：

- The Heritage Foundation
- American Enterprise Institute
- Hoover Institution
- Wilson Center
- Cato Institute
- Center for American Progress
- Atlantic Council
- National Bureau of Economic Research

### P2 英欧及国际安全来源

用于补充欧洲对华、国际安全、全球治理和经贸政策视角：

- Chatham House
- IISS
- ECFR
- Bruegel
- IFRI
- CEPR
- ifo Institute
- SWP
- DGAP
- SIPRI

### P3 周边国家和区域经济来源

用于补充中国周边国家和区域组织视角：

- JIIA
- RIETI
- KIEP
- KDI
- ERIA

### P4 待人工校对池

来自附件 Top 100 或其他批量名单的机构，进入正式监测前至少需要确认：

- 中文名和英文名是否准确；
- 国家、机构类型是否准确；
- 官网是否可访问；
- 是否存在 RSS、报告库、出版物页或专题页；
- 是否经常发布不少于 20 页的英文研究报告；
- 是否与涉华、印太、中美关系、全球治理、安全、经贸、科技或产业政策相关。
- 是否属于老师附件中的泛称、疑似重复项或 PDF 提取名称不完整项；这类条目需人工确认后再进入正式来源配置。

## 已实现的数据字段

当前 `think_tanks` 表已增加以下来源治理字段：

- `priority_tier`：P0/P1/P2/P3/P4
- `region_focus`：us/europe/neighboring/international/domestic/candidate
- `is_verified`：是否已完成人工校对

`source_notes` 暂未单独建字段，来源入口、报告类型和抓取注意事项先继续记录在文档、解析器配置和候选报告诊断中。

`sources.url` 采用全局唯一口径：同一个官网、RSS、报告库或专题页 URL 只归属一个机构，不重复挂载到多个机构下。批量种子脚本发现 URL 已存在时会跳过创建，避免后续抓取、去重和健康诊断出现重复来源。

## 入库试运行口径

机构优先级和入库试运行状态分开管理。P0/P1 表示研究价值和开发优先级较高，但不自动代表该来源可以批量写入报告库。

当前准入状态以 [source-rollout-status.md](source-rollout-status.md) 为准：

- `pilot_crawl`：已通过小样本文档复核，可小批量写入报告库。
- `discovery_only`：只做候选发现和只读审计，暂不写入正式报告库。
- `blocked`：入口不可稳定访问或受站点防护影响，需先解决可达性。
- `standard_review`：尚未完成小样本复核，进入入库前必须先审计。

单个来源从入口盘点、只读审计、人工试写、AI 复核到升级或停用的操作流程，
统一按 [source-onboarding-playbook.md](source-onboarding-playbook.md) 执行。

P0/P1 美国重点来源的阶段性运行结论和下一步优先级见
[p0-p1-source-stage-report-20260921.md](p0-p1-source-stage-report-20260921.md)。

## 开发顺序建议

1. 保持当前表结构，先清理明显错误的种子数据。
2. 先按老师 Word 名单补齐未接入重点机构的只读审计，不直接批量写入数据库。
3. 与老师确认是否需要国内机构进入第一阶段监测。
4. 基于 `priority_tier` 和 `region_focus` 优先补齐 P0/P1 来源解析器。
5. 后续如需记录更细的抓取注意事项，再单独评估是否新增 `source_notes` 字段。
6. 每批新增来源都用候选报告明细验证：抓到了什么、跳过了什么、为什么跳过。
7. 验证解析器时重点抽查 `substantial` 入库样本，确认“标题不显性涉华但正文实质涉华”的报告没有被误删，也确认零散提及中国的 `incidental` 报告不会入库。
