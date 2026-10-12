# 来源治理数据质量清单

更新时间：2026-09-19

本文档基于 `backend/app/scripts/seed_thinktank_data.py` 中的 123 个机构条目，以及
`backend/app/scripts/source_governance.py` 的优先级规则生成。用途是指导后续补官网、
订阅源、解析器和人工核验，不直接代表已可稳定抓取的来源数量。

## 总览

| 指标 | 数量 | 说明 |
| --- | ---: | --- |
| 机构总数 | 123 | 当前种子清单总量 |
| 已配置官网 | 50 | 可进一步诊断网站结构 |
| 缺官网 | 73 | 主要来自 Top 100 附件导入，需人工核对 |
| 已配置 RSS | 4 | Brookings、CSIS、RAND、Atlantic Council |
| 缺 RSS | 119 | 后续需要补 RSS、报告页解析器或站内搜索策略 |
| 已核验来源 | 29 | P0/P1/P2/P3 和国内参照源 |
| 候选未核验来源 | 94 | 默认 P4 candidate，暂不应作为高可信自动抓取来源 |

## 优先级分布

| 优先级 | 数量 | 当前含义 |
| --- | ---: | --- |
| P0 | 6 | 美国核心顶级来源，优先保证抓取质量 |
| P1 | 8 | 美国重点来源，第二优先级 |
| P2 | 8 | 欧洲重点来源 |
| P3 | 5 | 周边国家和区域重点来源 |
| P4 | 96 | 国内参照源和候选来源 |

## 区域分布

| 区域 | 数量 | 当前含义 |
| --- | ---: | --- |
| us | 14 | 美国核心/重点来源 |
| europe | 8 | 欧洲重点来源 |
| neighboring | 5 | 日本、韩国、东盟等周边来源 |
| domestic | 2 | 国内参照源 |
| candidate | 94 | 待核验候选来源 |

## 已有 RSS 来源

| key | 机构 | 优先级 | 区域 |
| --- | --- | --- | --- |
| `brookings` | Brookings Institution | P0 | us |
| `csis` | Center for Strategic and International Studies | P0 | us |
| `rand` | RAND Corporation | P0 | us |
| `atlantic_council` | Atlantic Council | P1 | us |

## 第一批仍待补 RSS 或专用解析器

这些来源已经核验为重点来源，但目前没有 RSS，也尚未接入基础网站解析器。
后续开发应优先为它们补订阅源、报告页解析器或站内搜索策略。

| key | 机构 | 优先级 | 区域 | 建议动作 |
| --- | --- | --- | --- | --- |
| 暂无 | - | - | - | P0/P1 美国重点来源均已有 RSS、基础网站解析器或专用解析器；下一步以真实抓取复核为主 |

## 已有基础网站解析器但仍需真实抓取复核

这些来源已经具备基础网站解析器或独立解析器，但仍应通过真实抓取检查 found/saved/skipped
分布，确认是否能稳定产出 20 页以上报告或足够长的网页长文。

| key | 机构 | 优先级 | 区域 | 当前入口 |
| --- | --- | --- | --- | --- |
| `brookings` | Brookings Institution | P0 | us | 独立 Brookings 解析器 |
| `csis` | Center for Strategic and International Studies | P0 | us | 独立 CSIS 解析器和 RSS |
| `rand` | RAND Corporation | P0 | us | RSS + 核心网站解析器 |
| `cfr` | Council on Foreign Relations | P0 | us | 核心网站解析器 |
| `carnegie` | Carnegie Endowment for International Peace | P0 | us | 核心网站解析器 |
| `piie` | Peterson Institute for International Economics | P0 | us | 核心网站解析器 |
| `heritage` | The Heritage Foundation | P1 | us | 核心网站解析器 |
| `aei` | American Enterprise Institute | P1 | us | 核心网站解析器 |
| `hoover` | Hoover Institution | P1 | us | 核心网站解析器 |
| `wilson` | Woodrow Wilson International Center for Scholars | P1 | us | 核心网站解析器；真实发现仍需专项增强 |
| `cato` | Cato Institute | P1 | us | 规则已配置；普通 HTTP 当前被 Incapsula 防护拦截 |
| `cap` | Center for American Progress | P1 | us | 专用 CAP 解析器 |
| `nber` | National Bureau of Economic Research | P1 | us | NBER 搜索 API 解析器 |
| `atlantic_council` | Atlantic Council | P1 | us | RSS |

## 第二批待补来源

这些来源已经被治理规则标记为欧洲、周边或国内重点参照源，但目前还没有 RSS。

| key | 机构 | 优先级 | 区域 |
| --- | --- | --- | --- |
| `bruegel` | Bruegel | P2 | europe |
| `chatham_house` | Chatham House | P2 | europe |
| `ifri` | French Institute of International Relations | P2 | europe |
| `swp` | German Institute for International and Security Affairs | P2 | europe |
| `dgap` | German Council on Foreign Relations | P2 | europe |
| `ecfr` | European Council on Foreign Relations | P2 | europe |
| `iiss` | International Institute for Strategic Studies | P2 | europe |
| `sipri` | Stockholm International Peace Research Institute | P2 | europe |
| `jiia` | Japan Institute of International Affairs | P3 | neighboring |
| `rieti` | Research Institute of Economy, Trade and Industry | P3 | neighboring |
| `eria` | Economic Research Institute for ASEAN and East Asia | P3 | neighboring |
| `kdi` | Korea Development Institute | P3 | neighboring |
| `kiep` | Korea Institute for International Economic Policy | P3 | neighboring |
| `siis` | Shanghai Institutes for International Studies | P4 | domestic |
| `cicir` | China Institutes of Contemporary International Relations | P4 | domestic |

## 候选来源治理原则

当前 94 个候选来源默认是 `P4 + candidate + is_verified=False`。处理原则：

1. 先核官网，再补 RSS 或报告页入口。
2. 只有确认机构官网、内容类型和抓取入口后，才调整 `is_verified`。
3. 不因为机构名出现在 Top 100 附件里就直接进入重点抓取队列。
4. 候选来源即使能抓取，也应先进入低优先级观察队列，避免噪声污染老师端提醒。

## 候选但已有官网的来源

这些来源已经具备官网字段，可以优先做站点诊断和解析器可行性评估：

`cepr`, `leibniz`, `max_planck`, `helmholtz`, `fraunhofer`, `ifo`,
`ifw_kiel`, `diw`, `rwi`, `iwh`, `wzb`, `giga`, `zew`, `mpi_ic`,
`mpi_social`, `dlr`, `fzj`, `fraunhofer_isi`, `fraunhofer_imw`,
`fraunhofer_sit`, `fraunhofer_iao`

## 候选且缺官网的来源

这些来源需要先人工核对官网，再决定是否进入后续开发：

`amnesty_international`, `transparency_international`, `fgv`,
`fraser_institute`, `international_crisis_group`, `ceps`,
`carnegie_moscow_center`, `cass`, `adbi`, `kas`, `fes`, `imemo_ras`,
`clingendael`, `martens_centre`, `ciis`, `carnegie_middle_east_center`,
`cari`, `diis`, `ideas`, `cigi`, `rusi`, `wef`, `human_rights_watch`,
`drc_china`, `ccs_india`, `acpss`, `iea_uk`, `lyd`, `lowy_institute`,
`odi`, `fanrpan`, `bicc`, `cidob`, `prio`, `eai_korea`, `iiss_china`,
`aerc`, `accord`, `razumkov_centre`, `rand_europe`, `pism`,
`case_poland`, `demos_uk`, `csis_indonesia`, `cer`, `euiss`, `nupi`,
`tesev`, `ecipe`, `civitas`, `ifans`, `siia`, `fride`, `idss`,
`saiia`, `die_germany`, `faes`, `ccr_south_africa`, `iai`, `hbs`,
`alt_turkey`, `timbro`, `cps_uk`, `cpps_malaysia`, `cep_chile`,
`iseas`, `ids_uk`, `elcano`, `flacso`, `atps`, `bids`, `svop`, `idsa`

## 建议验收标准

每补齐一个来源，至少完成以下检查：

1. `website` 指向机构主站或稳定研究入口，不使用搜索结果页。
2. 如有 RSS，RSS 能返回最近内容，且标题/链接可解析。
3. 如无 RSS，专用解析器能提取报告标题、链接、发布时间和 PDF/正文入口。
4. 爬虫能把 `direct` 和 `substantial` 涉华报告入库，过滤 `incidental` 和 `unrelated`。
5. 对单个来源跑一次真实抓取，并记录 found/saved/skipped 分布。

## 入库试运行策略

真实抓取闭环小样本复核后，新增 `source_rollout_policy` 作为入库前策略层。
该策略不改变机构优先级，也不写入数据库；它只用于判断某个来源是否适合进入第一批试运行抓取。

当前完整口径见 [source-rollout-status.md](source-rollout-status.md)。

| 策略 | 含义 |
| --- | --- |
| `pilot_crawl` | 已通过小样本文档复核，可进入小批量入库抓取试点 |
| `discovery_only` | 只保留候选发现，暂不建议批量入库 |
| `blocked` | 来源入口当前不可稳定访问，需先解决可达性 |
| `standard_review` | 尚未完成小样本复核，进入入库前需先审计 |

当前第一批：

- `brookings`、`cfr`、`csis`、`piie`：`pilot_crawl`
- `aei`：`pilot_crawl`，允许网页长文进入自动入库试运行；现有 8 篇入库样本已全部前端复核通过，但仍每次最多新增 1 篇并继续人工复核
- `cap`、`cato`、`heritage`：`blocked`，需先确认稳定入口、官方 feed、授权 API 或人工维护方式
- 其他来源：`standard_review`，进入入库前必须先完成只读审计

AEI 阶段收尾结论：

- AEI 网页长文可作为补充文档形态，但不能替代质量复核。转载页、导流页和合作机构原始页需要单独识别。
- 报告 356 已从 AEI 导流页切换到 Asia Society 原始全文页，并完成重新生成 AI 与前端批准。
- 后续 AEI 继续使用小批量策略，重点记录新增样本的正文长度、来源 URL、AI 成果结构和人工复核结论。
