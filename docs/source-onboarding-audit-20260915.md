# 来源接入闭环审计记录

审计日期：2026-09-15

## 审计范围

本次只读审计面向 P0/P1 境外涉华重点来源，不写数据库、不发通知、不调用 LLM。

已执行两类检查：

- 发现阶段：访问来源入口，确认能否发现候选报告。
- 文档阶段：对代表性来源每个最多检查 2 条候选，确认能否取得 20 页以上 PDF 或足够长的网页长文。

## 主要结论

### 建议进入小批量入库试运行

| 机构 | 发现候选 | 文档结果 | 建议 |
| --- | ---: | --- | --- |
| Brookings | 7 | 2/2 为网页长文，正文约 17681-24997 字符 | 可按网页长文正式入库口径试运行 |
| CFR | 4 | 2/2 为 PDF，20 页和 96 页 | 可优先试运行 |
| PIIE | 4 | 2/2 为 PDF，37 页和 56 页 | 可优先试运行 |

### 建议暂缓批量入库

| 机构 | 发现候选 | 文档结果 | 暂缓原因 |
| --- | ---: | --- | --- |
| Heritage | 9 | 2/2 抓取正文时 403 | 需寻找官方 feed、可访问入口或授权方式 |
| CAP | 1 | 1/1 抓取正文时 403 | 需寻找官方 feed、可访问入口或授权方式 |
| AEI | 13 | 2/2 未取得合格 PDF/网页正文 | 召回价值高，但需继续调试正文抽取或入口 |

## 其他发现

- Brookings RSS 当前返回 HTML 或跳转结果，暂不适合作为稳定 RSS 来源；Brookings website 入口可用。
- Atlantic Council RSS 召回量高，但混有新闻、博客、短评论和活动内容，暂不作为第一批报告入库主线。
- CSIS RSS 当前样本多为旧活动内容，website 入口本次未发现候选，需要单独修复召回策略。
- Cato 普通入口发现为 0，延续此前“站点防护或入口不可用”的判断。

## 本次策略调整

- 将 `brookings`、`cfr`、`piie` 标记为可小批量入库试运行。
- 将 `heritage`、`cap`、`cato` 标记为入口阻塞，待找到更稳定入口后再进入试运行。
- `aei` 保持仅发现阶段，但保留网页长文正式入库口径。

## 小批量真实入库试运行记录

### 2026-09-17

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.pilot_crawl_sources --keys brookings,cfr,piie --max-saved 1 --max-candidates 5 --ai-status skipped
```

执行口径：

- 真实写入抓取运行记录。
- 每个来源最多保存 1 篇新报告。
- 默认不创建通知。
- 新报告 AI 状态设为 `skipped`，避免自动排队。

执行结果：

| 机构 | crawl_run_id | 发现候选 | 新增入库 | 主要结果 |
| --- | ---: | ---: | ---: | --- |
| Brookings | 497 | 5 | 0 | 4 条已入库重复；1 条因页面未发现 PDF 链接跳过 |
| CFR | 498 | 5 | 0 | 5 条均为已入库重复 |
| PIIE | 499 | 4 | 0 | 4 条均为已入库重复 |

补充核查：

- Brookings 当前已有 10 篇入库报告，AI 状态均为 `success`。
- CFR 当前已有 5 篇入库报告，AI 状态均为 `success`。
- PIIE 当前已有 4 篇入库报告，AI 状态均为 `success`。

结论：

- `brookings`、`cfr`、`piie` 的去重链路正常，本次试运行未产生新的报告样本。
- 三个来源已有样本均已完成 AI 翻译和分析，本轮无需额外调用 LLM。
- 下一步应优先处理 CSIS、AEI、Heritage、CAP 的入口、召回和正文抽取问题。

### 2026-09-19

执行命令：

```powershell
docker exec thinktank-backend python -m app.scripts.pilot_crawl_sources --keys brookings,cfr,piie --max-saved 1 --max-candidates 5 --ai-status skipped
```

执行口径：

- 使用当前 `source_rollout_policy`，仅允许 `pilot_crawl` 来源进入试运行。
- 真实写入抓取运行记录。
- 每个来源最多保存 1 篇新报告。
- 默认不创建通知。
- 新报告 AI 状态设为 `skipped`，避免自动排队。

执行结果：

| 机构 | crawl_run_id | 发现候选 | 新增入库 | 主要结果 |
| --- | ---: | ---: | ---: | --- |
| Brookings | 508 | 5 | 0 | 4 条已入库重复；1 条因页面未发现 PDF 链接跳过 |
| CFR | 509 | 5 | 0 | 5 条均为已入库重复 |
| PIIE | 510 | 4 | 0 | 4 条均为已入库重复 |

结论：

- `brookings`、`cfr`、`piie` 当前试运行入口仍能正常发现候选。
- 本轮未新增报告，主要原因是候选已全部或基本全部入库。
- 去重链路继续正常工作；本轮未触发 AI 处理，也未创建老师端通知。
- 下一步不宜继续反复试抓同一批候选，应转向复核既有样本质量，或处理 CSIS、AEI、Heritage、CAP 等尚未稳定的来源。

## 重点来源修复前只读诊断

### 2026-09-17

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.audit_source_documents --keys csis,aei,heritage,cap --max-candidates 3 --discovery-timeout 90 --document-timeout 120
```

执行口径：

- 只读诊断，不写数据库。
- 不创建通知。
- 不调用 LLM。
- 每个来源最多检查 3 条候选文档。

执行结果：

| 机构 | 阶段策略 | 发现候选 | 检查候选 | 文档成功 | 主要失败点 |
| --- | --- | ---: | ---: | ---: | --- |
| CSIS | standard_review | 0 | 0 | 0 | 官网入口当前未召回候选，需要修复发现入口或改用专题/报告页 |
| AEI | discovery_only | 13 | 3 | 0 | 能发现报告页，但 PDF/正文获取不合格；2 条未发现 PDF，1 条页数 16 页低于 20 页 |
| Heritage | blocked | 9 | 3 | 0 | 候选充足，但文档抓取均返回 403 Forbidden |
| CAP | blocked | 1 | 1 | 0 | 候选较少，文档抓取返回 403 Forbidden |

样本失败摘要：

- CSIS：`https://www.csis.org/` 本轮发现候选为 0。
- AEI：
  - `Flipping the Script: How to Hold China's New Carriers at Risk`：页面未发现 PDF 链接。
  - `Dataset: China Global Investment Tracker`：页面未发现 PDF 链接。
  - `China's Outbound Investment Shrugs Off the Iran War`：PDF 仅 16 页，低于 20 页门槛。
- Heritage：
  - `Winning the New Cold War: A Plan for Countering China`：403 Forbidden。
  - `Xi Comes to Washington: Expectations for the Trump-Xi Summit`：403 Forbidden。
  - `Armed by China: The Dependency Behind Pakistan's Military`：403 Forbidden。
- CAP：
  - `The U.S. and China Must Explore Pacing the Frontier During September AI Dialogue`：403 Forbidden。

修复优先级判断：

1. 优先修 CSIS。CSIS 属于 P0 来源，但当前 website 入口召回为 0，应先确认稳定入口，例如 `/analysis`、China 专题页、报告页或可用 RSS。
2. 第二优先修 AEI。AEI 召回能力较好，问题集中在 PDF 链接识别、网页长文兜底和 20 页门槛判断。
3. Heritage 和 CAP 暂缓自动抓取。当前主要问题是访问层 403，宜先寻找官方 feed、站点地图、公开 PDF 入口、授权 API 或人工维护入口。

### 2026-09-18 CSIS 修复跟进

本轮已对 CSIS 解析器做兼容增强：

- 保留旧结构 `article.report-search-listing`。
- 新增兼容当前页面中出现的 `.views-row` / `.search-result` 结构。
- 仅接收明确标记为 `Report` 的结果，继续过滤 Commentary、Event、Podcast、Newsletter、Transcript 等轻量内容。
- 增加 China 区域页、China Power Project 页和 Report 筛选页作为发现入口；单个入口失败时继续尝试其他入口。

验证结果：

- 相关单元测试和 ruff 检查通过。
- 当时真实只读审计 `csis` 仍为 `raw_candidates=0`。
- 当前可访问的 `/analysis`、China 区域页和 China Power Project 页前列结果主要是 Commentary、Event、Podcast、Blog Post、Congressional Testimony 等，未出现可保守入库的 `Report`。
- Report 筛选页、分页和关键词搜索入口在当前运行环境出现 403 或连接失败；CSIS RSS 仍返回 2016 年旧活动内容，不适合作为报告召回来源。

结论：

- CSIS 解析器已具备兼容新结构的能力，但公开可访问入口仍不能稳定召回报告。
- 短期不建议继续扩大 CSIS 自动抓取范围；可保留现有代码增强，等待找到稳定公开入口、可用 API、站点地图策略或人工维护入口后再进入试运行。
- 下一步优先转向 AEI，因为 AEI 已能稳定发现候选，问题更集中在 PDF/正文抽取策略。

### 2026-09-19 CSIS sitemap 补充召回修复

本轮继续修复 CSIS 召回入口，目标是提高正式报告发现能力，同时避免把
Digital Feature、Commentary、Event 等轻量内容误收为报告。

调整内容：

- `article.report-search-listing` 不再无条件入库为候选，必须识别为 `Report`。
- 兼容 CSIS 卡片中的 `Report by ...` 和 `Report — 日期` 两种类型标识。
- 新增 CSIS sitemap 补充入口：
  - 读取公开 `https://www.csis.org/sitemap.xml`。
  - 仅筛选 URL 路径为 `/analysis/` 且 URL 自身带涉华信号的页面。
  - 打开候选页面后，只有确认页面存在 PDF 下载链接，才作为报告候选。
  - 候选页面打开数量限制为 20，避免把历史 sitemap 全量页面塞进抓取链路。

验证结果：

- 相关单元测试和 ruff 检查通过。
- 后端全量测试通过：153 个测试通过。
- 真实只读发现 `csis` 从 1 条正式 Report 候选扩展到 8 条候选。
- 真实只读文档审计结果如下：

| 机构 | 阶段策略 | 发现候选 | 检查候选 | 文档成功 | 主要结果 |
| --- | --- | ---: | ---: | ---: | --- |
| CSIS | standard_review | 8 | 3 | 2 | 1 条当前列表 Report 仅 18 页未过门槛；2 条 sitemap 涉华 PDF 报告均为 21 页并通过 |

样本结果：

| 样本 | 结果 | 说明 |
| --- | --- | --- |
| Beyond the Memory Cycle: AI, HBM, and the New Semiconductor Shortage | 失败 | PDF 18 页，低于 20 页门槛，且不是明显涉华报告 |
| Assessing the Impact of China-Russia Security Coordination in Latin America and the Caribbean | 通过 | PDF 21 页，文本约 59,360 字符 |
| Assessing the Impact of China-Russia Coordination in the Media and Information Space | 通过 | PDF 21 页，文本约 58,748 字符 |

结论：

- CSIS 召回已从“当前公开列表无稳定涉华报告”改善为“可通过 sitemap 补充发现涉华 PDF 报告”。
- 当前仍保持 `standard_review`，不直接进入自动入库试运行。
- 下一步建议对 CSIS 执行一次每次最多保存 1 篇、AI 状态 `skipped` 的小批量人工试运行；若入库样本质量通过，再评估是否将 CSIS 调整为 `pilot_crawl`。

### 2026-09-19 CSIS 小批量人工试写

执行命令：

```powershell
docker exec thinktank-backend python -m app.scripts.pilot_crawl_sources --keys csis --allow-standard-review --max-saved 1 --max-candidates 5 --ai-status skipped
```

执行口径：

- CSIS 仍保持 `standard_review`，本轮通过显式 `--allow-standard-review`
  做人工小样本试写。
- 默认不创建通知。
- 新报告 AI 状态设为 `skipped`，避免自动排队。
- 每个来源最多保存 1 篇。

执行结果：

| 机构 | source_id | crawl_run_id | 发现候选 | 新增入库 | 主要结果 |
| --- | ---: | ---: | ---: | ---: | --- |
| CSIS | 5 | 562 | 5 | 1 | 1 条 PDF 页数不足跳过；1 条 PDF 报告入库 |
| CSIS | 55 | 563 | 5 | 1 | 同一机构存在第二个 active website 来源，导致同一报告再次入库 |

新增报告：

| 报告 ID | source_id | 标题 | 正文类型 | 页数 | AI 状态 |
| ---: | ---: | --- | --- | ---: | --- |
| 383 | 5 | Assessing the Impact of China-Russia Security Coordination in Latin America and the Caribbean | `pdf` | 21 | `skipped` |
| 384 | 55 | Assessing the Impact of China-Russia Security Coordination in Latin America and the Caribbean | `pdf` | 21 | `skipped` |

问题与修复：

- 本轮发现 CSIS 同一机构下存在两个 active website 来源：
  `https://www.csis.org/analysis` 和 `https://www.csis.org/`。
- 试运行脚本原先按来源逐个执行，且只按同一 `source_id`
  检查重复，因此同一 URL 可在不同 source 下重复入库。
- 已修复 `pilot_crawl_sources`：
  - 同一机构 key 只选择一个 website 来源执行试运行。
  - 试运行重复检查改为跨全部 reports 的 `normalized_url`，避免跨来源重复入库。

结论：

- CSIS sitemap 补充入口可以产出通过 20 页门槛的涉华 PDF 报告样本。
- 报告 383/384 是同一篇报告的重复入库样本，建议保留其中一条用于人工复核，清理另一条重复记录。
- 在重复来源清理前，不建议把 CSIS 调整为 `pilot_crawl`。

### 2026-09-19 CSIS 重复样本清理

清理对象：

- 保留报告 383：`source_id=5`，AI 状态 `skipped`。
- 删除报告 384：`source_id=55`，与报告 383 的 `normalized_url` 完全一致。

删除前备份：

- `docs/backups/20260919-csis-duplicate-cleanup/report-384-before-delete.json`

清理后核验：

| URL | 剩余报告数 | 保留报告 ID | 删除报告 ID |
| --- | ---: | ---: | ---: |
| `https://www.csis.org/analysis/assessing-impact-china-russia-security-coordination-latin-america-and-caribbean` | 1 | 383 | 384 |

结论：

- CSIS 本次人工试写样本已清理为单条记录。
- 后续试运行脚本已改为同一机构 key 只选择一个 website 来源，并跨全部 reports 检查 `normalized_url`，避免同一 URL 因不同 source 重复入库。
- 下一步可在前端人工复核报告 383 的 PDF 正文质量；通过后再决定是否手动触发 AI 或调整 CSIS rollout 状态。

### 2026-09-19 CSIS 报告 383 AI 处理结果

处理对象：

| 报告 ID | 来源 | 标题 | 页数 | 正文类型 |
| ---: | --- | --- | ---: | --- |
| 383 | CSIS | Assessing the Impact of China-Russia Security Coordination in Latin America and the Caribbean | 21 | `pdf` |

正文质量核验：

| 字段 | 结果 |
| --- | ---: |
| PDF 字节数 | 825,775 |
| 抽取正文长度 | 59,360 字符 |
| 非空页数 | 21 |
| 乱码替换符 | 0 |

AI 处理过程：

- 已将报告 383 的 AI 状态从 `skipped` 调整为 `pending`，并只对该报告触发 AI 分块处理。
- 共生成 25 个 AI 分块任务：21 个 translation chunk、4 个 analysis chunk。
- 所有分块任务均执行成功。
- finalizer 汇总阶段已完成；其中深层研判因字数边界自动重试，最终第 4 次产出通过长度校验。

AI 处理结果：

| 字段 | 结果 |
| --- | ---: |
| AI 状态 | `success` |
| 全文翻译长度 | 17,493 字符 |
| 主要观点长度 | 1,649 字符 |
| 主要观点编号分论点 | 4 个 |
| 深层研判长度 | 2,237 字符 |
| 深层研判编号分论点 | 5 个 |
| 复核状态 | `pending_review` |
| AI 生成时间 | 2026-09-19 15:30:51 |

结论：

- 报告 383 的全文翻译稿、主要观点和深层研判均已生成成功。
- 主要观点处于 1500-2000 字目标区间，深层研判处于 2000-2500 字目标区间，且均具备显式编号分论点。
- CSIS 的 sitemap 补充召回、PDF 正文抽取、AI 分块处理和 finalizer 汇总链路已跑通一个有效样本。
- CSIS 仍建议暂时保持 `standard_review`，先在前端完成报告 383 的人工质量复核，再决定是否升级为 `pilot_crawl`。

### 2026-09-21 CSIS 报告 383 前端复核结果

复核结论：

- 报告 383 前端页面质量合格。
- 已将报告 383 的复核状态从 `pending_review` 更新为 `approved`。
- 复核意见记录为：`前端页面质量合格。`
- 更新前备份已保存到
  `docs/backups/20260921-report-383-approved/report-383-before-approval.json`。

当前状态：

| 字段 | 结果 |
| --- | --- |
| AI 状态 | `success` |
| 复核状态 | `approved` |
| 复核历史 | 已写入 1 条通过记录 |

结论：

- CSIS 已完成一个从 sitemap 召回、PDF 入库、AI 生成到前端人工复核通过的完整闭环样本。
- 下一步可评估是否将 CSIS 从 `standard_review` 升级为 `pilot_crawl`，继续采用每次最多新增 1 篇、人工复核后再扩大的节奏。

### 2026-09-21 CSIS 升级为 pilot_crawl

调整依据：

- 报告 383 已完成从 sitemap 召回、PDF 文档入库、AI 翻译评论生成到前端人工复核通过的完整闭环。
- 试运行脚本已修复同一机构多个 website 来源导致的跨 source 重复入库问题。
- 试运行重复检查已改为跨全部 reports 的 `normalized_url`，可降低同一 URL 重复保存风险。

策略调整：

| 来源 | 调整前 | 调整后 | 文档策略 | 节奏 |
| --- | --- | --- | --- | --- |
| CSIS | `standard_review` | `pilot_crawl` | `pdf_20_page_required` | 每次最多新增 1 篇，人工复核后再扩大 |

结论：

- CSIS 进入 P0 小批量自动入库试运行来源。
- 仍保留 20 页 PDF 门槛，不放宽为网页长文入库。
- 后续应重点观察 sitemap 候选召回稳定性、短 PDF 跳过率和通知噪声。

### 2026-09-21 CSIS pilot_crawl 正式试抓

执行命令：

```bash
docker exec thinktank-backend python -m app.scripts.pilot_crawl_sources --keys csis --max-saved 1 --max-candidates 5 --ai-status skipped
```

运行结果：

| 来源 | source_id | crawl_run_id | 发现候选 | 新增入库 | 主要结果 |
| --- | ---: | ---: | ---: | ---: | --- |
| CSIS | 5 | 621 | 5 | 0 | 3 条已入库重复；2 条 PDF 页数不足 |

跳过样例：

- `Beyond the Memory Cycle: AI, HBM, and the New Semiconductor Shortage`：PDF 18 页，低于 20 页门槛。
- `Outcompete the World: Revisiting U.S. Economic Priorities in the Competition with China in Latin America and ...`：PDF 11 页，低于 20 页门槛。
- `Assessing the Impact of China-Russia Security Coordination in Latin America and the Caribbean`：已入库重复。
- `Assessing the Impact of China-Russia Coordination in the Media and Information Space`：已入库重复。
- `Taiwan and the Pacific`：已入库重复。

核验结论：

- CSIS 已能不带 `--allow-standard-review` 通过 `pilot_crawl` 准入校验并完成正式试抓。
- 本轮没有新增报告，说明跨 reports 的 `normalized_url` 去重保护生效。
- 试抓前数据库中已有 17 条 CSIS 报告，最新报告 ID 为 389；本轮试抓后仍为 17 条。
- 当前 CSIS 仍存在两个 active website 来源：
  - `source_id=5`：`https://www.csis.org/analysis`
  - `source_id=55`：`https://www.csis.org/`
- 本轮正式试抓只执行 `source_id=5`，说明“同一机构 key 只选择一个 website 来源”的脚本保护生效。
- 试抓前已存在 `source_id=55` 下的 CSIS 记录 387、388、389，后续建议单独评估是否清理重复记录或停用重复 website 来源。

### 2026-09-21 CSIS 重复来源停用与重复报告清理

清理对象：

| 对象 | 处理 |
| --- | --- |
| `source_id=55` / `https://www.csis.org/` | 停用，保留 `source_id=5` / `https://www.csis.org/analysis` 作为 CSIS pilot_crawl 入口 |
| 报告 387 | 删除，保留同 URL 报告 383 |
| 报告 388 | 删除，保留同 URL 报告 385 |
| 报告 389 | 删除，保留同 URL 报告 386 |

清理前备份：

- `docs/backups/20260921-csis-source55-cleanup/source55-and-reports-387-389-before-cleanup.json`

清理后核验：

| URL | 清理后保留报告 | source_id |
| --- | ---: | ---: |
| `https://www.csis.org/analysis/assessing-impact-china-russia-security-coordination-latin-america-and-caribbean` | 383 | 5 |
| `https://www.csis.org/analysis/assessing-impact-china-russia-coordination-media-and-information-space` | 385 | 5 |
| `https://www.csis.org/analysis/taiwan-and-pacific` | 386 | 5 |

结果：

- `source_id=55` 已设为 inactive，并记录停用原因。
- 报告 387、388、389 已删除。
- 相关 AI 分块已随报告删除级联清理，残留分块数为 0。
- CSIS 报告总数从 17 条降为 14 条。
- 清理后快照已保存到
  `docs/backups/20260921-csis-source55-cleanup/source55-and-reports-387-389-after-cleanup.json`。

### 2026-09-21 CSIS 报告 385/386 前端复核结果

复核对象：

| 报告 ID | 标题 | AI 状态 | 复核结果 |
| ---: | --- | --- | --- |
| 385 | Assessing the Impact of China-Russia Coordination in the Media and Information Space | `success` | 合格 |
| 386 | Taiwan and the Pacific | `success` | 合格 |

处理结果：

- 已将报告 385、386 的复核状态从 `pending_review` 更新为 `approved`。
- 复核意见均记录为：`前端页面质量合格。`
- 更新前备份已保存到
  `docs/backups/20260921-csis-385-386-approved/reports-385-386-before-approval.json`。

结论：

- CSIS 目前已有 3 篇完整闭环且前端复核合格样本：383、385、386。
- CSIS 的 sitemap 召回、PDF 抽取、AI 生成和前端复核链路在多样本上表现稳定。
- 短期仍建议保持每次最多新增 1 篇，并继续人工复核，不立即放大抓取规模。

### 2026-09-21 AEI playbook 只读核查

背景：

- AEI 当前策略仍为 `discovery_only` + `web_article_allowed`。
- 历史试运行已产生 8 篇 AEI 网页长文报告，均为 `ai_status=success`、`review_status=pending_review`。
- 本轮按 `source-onboarding-playbook.md` 重新核查，不直接升级为 `pilot_crawl`。

当前数据库状态：

| 报告 ID | 标题 | 翻译长度 | 主要观点长度 | 深层研判长度 | 复核状态 |
| ---: | --- | ---: | ---: | ---: | --- |
| 356 | Beyond the Biotech Race — Right-Sizing U.S.-China Competition in a Human-Centered Industry | 2,047 | 1,588 | 2,285 | `pending_review` |
| 380 | China’s Outbound Investment Shrugs Off the Iran War | 22,357 | 1,896 | 2,008 | `pending_review` |
| 381 | Connected and Autonomous Cars: Security Risks from Chinese Components | 12,535 | 1,583 | 2,192 | `pending_review` |
| 390 | The Lithography Loophole: How China Is Printing Its Way to Chip Self-Sufficiency | 13,616 | 1,568 | 2,237 | `pending_review` |
| 391 | Codifying Coercion: China’s Anti-Secession Law and the Threat to Taiwan’s Sovereignty | 9,415 | 1,788 | 2,073 | `pending_review` |
| 392 | When Does China Stop Growing (Entirely)? | 12,018 | 1,911 | 2,077 | `pending_review` |
| 393 | Steady, Not Soaring, Chinese Investment in 2025 | 23,884 | 1,518 | 2,007 | `pending_review` |
| 394 | Annual Wealth Estimates for China | 10,625 | 1,738 | 2,147 | `pending_review` |

只读审计命令：

```bash
docker exec thinktank-backend python -m app.scripts.audit_source_documents --keys aei --max-candidates 5 --discovery-timeout 90 --document-timeout 120
```

只读审计结果：

| 来源 | rollout 状态 | 原始候选 | 去重后候选 | 检查候选 | 文档通过 | 文档失败 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| AEI | `discovery_only` | 13 | 13 | 5 | 2 | 3 |

样本结论：

- `China’s Outbound Investment Shrugs Off the Iran War`：网页长文通过，正文约 53,498 字符。
- `Beyond the Biotech Race — Right-Sizing U.S.-China Competition in a Human-Centered Industry`：网页长文通过，正文约 6,666 字符。
- `Flipping the Script: How to Hold China’s New Carriers at Risk`、`Dataset: China Global Investment Tracker`、`Preventing the Erosion of Extended Deterrence in the Indo-Pacific`：未发现 PDF 链接，文档检查失败。

结论：

- AEI 召回能力稳定，但文档通过率仍不高，本轮 5 条样本中 2 条通过、3 条失败。
- 已入库的 8 篇 AEI 报告均已完成 AI，且主要观点、深层研判均处于目标字数区间。
- 进入下一步前，应先完成 AEI 已有 8 篇成果的前端人工复核；在 2-3 篇通过前，不建议把 AEI 从 `discovery_only` 升级为 `pilot_crawl`。
- 更新前状态备份保存到
  `docs/backups/20260921-aei-playbook-audit/aei-current-state-before-readonly-audit.json`。

### 2026-09-21 AEI 报告 380/381/390 前端复核结果

复核对象：

| 报告 ID | 标题 | AI 状态 | 复核结果 |
| ---: | --- | --- | --- |
| 380 | China’s Outbound Investment Shrugs Off the Iran War | `success` | 合格 |
| 381 | Connected and Autonomous Cars: Security Risks from Chinese Components | `success` | 合格 |
| 390 | The Lithography Loophole: How China Is Printing Its Way to Chip Self-Sufficiency | `success` | 合格 |

处理结果：

- 已将报告 380、381、390 的复核状态从 `pending_review` 更新为 `approved`。
- 复核意见均记录为：`前端页面质量合格。`
- 三篇报告均已写入复核历史。
- 更新前备份已保存到
  `docs/backups/20260921-aei-380-381-390-approved/reports-380-381-390-before-approval.json`。

结论：

- AEI 已有 3 篇 AI 成果通过前端人工复核。
- 从成果质量看，AEI 已满足进入 `pilot_crawl` 的样本数量要求。
- 但 AEI 只读审计仍显示 5 条样本中 3 条文档失败，因此若升级为 `pilot_crawl`，仍应保持每次最多新增 1 篇、人工复核后再扩大。

### 2026-09-21 AEI 升级为 pilot_crawl

调整依据：

- AEI 已有 3 篇前端人工复核合格样本：380、381、390。
- 8 篇已入库 AEI 报告均已完成 AI，主要观点和深层研判长度均处于目标区间。
- AEI 文档策略仍为 `web_article_allowed`，适合以网页长文报告形态继续小批量试运行。

策略调整：

| 来源 | 调整前 | 调整后 | 文档策略 | 节奏 |
| --- | --- | --- | --- | --- |
| AEI | `discovery_only` | `pilot_crawl` | `web_article_allowed` | 每次最多新增 1 篇，人工复核后再扩大 |

风险提示：

- AEI 只读审计仍显示文档通过率不高，本轮 5 条样本中 3 条失败。
- 因此 AEI 虽进入 `pilot_crawl`，但不适合放大抓取规模。
- 后续应重点观察网页长文质量、重复率、跳过原因和通知噪声。

### 2026-09-21 AEI pilot_crawl 正式试抓

执行命令：

```bash
docker exec thinktank-backend python -m app.scripts.pilot_crawl_sources --keys aei --max-saved 1 --max-candidates 5 --ai-status skipped
```

运行结果：

| 来源 | source_id | crawl_run_id | 发现候选 | 新增入库 | 主要结果 |
| --- | ---: | ---: | ---: | ---: | --- |
| AEI | 6 | 622 | 5 | 0 | 2 条已入库重复；3 条文档获取失败 |

跳过样例：

- `Flipping the Script: How to Hold China’s New Carriers at Risk`：报告详情页中未发现 PDF 链接。
- `Dataset: China Global Investment Tracker`：报告详情页中未发现 PDF 链接。
- `China’s Outbound Investment Shrugs Off the Iran War`：已入库重复。
- `Beyond the Biotech Race — Right-Sizing U.S.-China Competition in a Human-Centered Industry`：已入库重复。
- `Preventing the Erosion of Extended Deterrence in the Indo-Pacific`：报告详情页中未发现 PDF 链接。

核验结论：

- AEI 已能不带 `--allow-standard-review` 通过 `pilot_crawl` 准入校验并完成正式试抓。
- 本轮没有新增报告，AEI 报告总数仍为 8 条。
- 升级后策略确认为 `pilot_crawl` + `web_article_allowed`。
- 文档失败率仍偏高，后续继续保持每次最多新增 1 篇，并优先复核已有 391、392、393、394。
- 试抓前后快照已保存到：
  - `docs/backups/20260921-aei-pilot-crawl-run/aei-before-pilot-crawl.json`
  - `docs/backups/20260921-aei-pilot-crawl-run/aei-after-pilot-crawl.json`

### 2026-09-21 AEI 报告 391/392/393/394 前端复核结果

复核对象：

| 报告 ID | 标题 | AI 状态 | 复核结果 |
| ---: | --- | --- | --- |
| 391 | Codifying Coercion: China’s Anti-Secession Law and the Threat to Taiwan’s Sovereignty | `success` | 合格 |
| 392 | When Does China Stop Growing (Entirely)? | `success` | 合格 |
| 393 | Steady, Not Soaring, Chinese Investment in 2025 | `success` | 合格 |
| 394 | Annual Wealth Estimates for China | `success` | 合格 |

处理结果：

- 已将报告 391、392、393、394 的复核状态从 `pending_review` 更新为 `approved`。
- 复核意见均记录为：`前端页面质量合格。`
- 四篇报告均已写入复核历史。
- 更新前备份已保存到
  `docs/backups/20260921-aei-391-394-approved/reports-391-394-before-approval.json`。

结论：

- AEI 当前已有 7 篇前端人工复核合格样本：380、381、390、391、392、393、394。
- AEI 网页长文报告的 AI 生成质量在多样本上稳定。
- 剩余未通过复核的 AEI 已入库样本为 356，建议后续单独检查该样本是否过短或是否适合保留。

### 2026-09-21 AEI 报告 356 单独质量检查

检查对象：

| 报告 ID | 标题 | 正文类型 | AI 状态 | 复核状态 |
| ---: | --- | --- | --- | --- |
| 356 | Beyond the Biotech Race — Right-Sizing U.S.-China Competition in a Human-Centered Industry | `web_article` | `success` | `pending_review` |

结构指标：

| 字段 | 结果 |
| --- | ---: |
| 原文正文长度 | 6,666 字符 |
| 全文翻译长度 | 2,047 字符 |
| 主要观点长度 | 1,588 字符 |
| 深层研判长度 | 2,285 字符 |
| 主要观点显式编号分论点 | 0 个 |
| 深层研判显式编号分论点 | 0 个 |

质量观察：

- 原文末尾包含 `Continue reading at Asia Society.`，说明 AEI 页面可能是转载、摘要或导流页，而非完整报告正文。
- 全文翻译长度明显短于其他 AEI 合格样本，但与当前抽取到的原文长度大体匹配。
- 主要观点和深层研判字数达标，但没有显式使用“一、二、三、四”等编号分论点。

结论：

- 报告 356 不建议直接标记为 `approved`。
- 该样本应由人工决定是保留为短网页长文样本、标记为 `rejected`，还是后续尝试抓取 Asia Society 原始全文。
- 更新前备份已保存到
  `docs/backups/20260921-aei-356-review/report-356-before-review.json`。

处理决定：

- 选择暂缓通过，保持 `review_status=pending_review`。
- 已写入复核意见：`暂缓通过：AEI 页面可能为转载/摘要或导流页，后续尝试抓取 Asia Society 原始全文后再复核。`
- 暂缓处理前备份已保存到
  `docs/backups/20260921-aei-356-defer-original/report-356-before-defer-note.json`。

### 2026-09-21 AEI 报告 356 原始全文补抓 dry-run

新增脚本：

- `backend/app/scripts/refetch_original_fulltext.py`
- 默认只做 dry-run；只有传入 `--apply` 才会覆盖报告正文，并清空旧 AI 成果。
- 支持从当前报告页自动识别 `Continue reading at ...` 之类的原始全文链接。

验证命令：

```bash
docker exec thinktank-backend python -m app.scripts.refetch_original_fulltext 356 --preferred-domain asiasociety.org
```

dry-run 结果：

| 字段 | 结果 |
| --- | --- |
| 当前 AEI URL | `https://www.aei.org/research-products/report/beyond-the-biotech-race-right-sizing-u-s-china-competition-in-a-human-centered-industry/` |
| 识别到的原始全文 URL | `https://asiasociety.org/policy-institute/beyond-biotech-race-right-sizing-us-china-competition-human-centered-industry` |
| 当前正文长度 | 6,666 字符 |
| 原始全文抽取长度 | 84,076 字符 |
| 正文增量 | 77,410 字符 |

验证结论：

- 356 可以从 Asia Society 原始页抽取到明显更完整的正文。
- 本轮未覆盖数据库正文，356 仍保持 `pending_review`。
- 若后续执行 `--apply`，旧 translation、summary、commentary 会被清空，`ai_status` 会回到 `pending`，需要重新跑 AI 并前端复核。
- 是否同时把报告 `url` 更新为 Asia Society 原始 URL，需要单独确认；当前脚本默认不改 URL，除非传入 `--update-report-url`。

### 2026-09-21 AEI 报告 356 原始全文覆盖与 AI 重生成

执行命令：

```bash
docker exec thinktank-backend python -m app.scripts.refetch_original_fulltext 356 --preferred-domain asiasociety.org --apply --update-report-url
docker exec thinktank-backend python -m app.scripts.reset_report_ai 356
```

处理结果：

| 字段 | 结果 |
| --- | --- |
| 原 AEI URL | `https://www.aei.org/research-products/report/beyond-the-biotech-race-right-sizing-u-s-china-competition-in-a-human-centered-industry/` |
| 更新后 URL | `https://asiasociety.org/policy-institute/beyond-biotech-race-right-sizing-us-china-competition-human-centered-industry` |
| 正文长度 | 6,666 -> 84,076 字符 |
| 正文增量 | 77,410 字符 |
| 删除旧 AI chunks | 3 个 |
| 重新生成 AI chunks | 37 个，全部成功 |
| translation 长度 | 25,057 字符 |
| summary 长度 | 1,538 字符，4 个编号分论点 |
| commentary 长度 | 2,266 字符，6 个编号分论点 |
| AI 状态 | `success` |
| 复核状态 | `pending_review` |
| AI 生成时间 | `2026-09-21 11:28:06` |

验证结论：

- 报告 356 已从 AEI 导流页切换为 Asia Society 原始全文页，正文质量明显改善。
- 旧 AI 成果和旧 chunks 已清理，当前 translation、summary、commentary 均基于新原文重新生成。
- 356 仍不直接标记为 `approved`，需要在前端完成最终人工复核。
- 覆盖前备份已保存到
  `docs/backups/20260921-aei-356-apply-original/report-356-before-apply-original.json`。

### 2026-09-21 AEI 报告 356 前端复核通过

复核结果：

| 字段 | 结果 |
| --- | --- |
| 报告 ID | 356 |
| AI 状态 | `success` |
| 复核状态 | `approved` |
| 复核时间 | `2026-09-21 11:35:16` |
| 复核意见 | `前端复核合格：已补抓 Asia Society 原始全文并重新生成 AI 成果，翻译稿、主要观点和深层研判质量通过。` |

结论：

- AEI 356 已完成“原始全文补抓 -> AI 重生成 -> 前端人工复核 -> 批准”闭环。
- 至此，AEI 现有 8 篇入库样本均已完成前端复核并通过。
- 批准前备份已保存到
  `docs/backups/20260921-aei-356-approve/report-356-before-approve.json`。

### 2026-09-21 Brookings 首批历史样本复核通过

复核结果：

| 报告 ID | 标题 | AI 状态 | 复核状态 |
| --- | --- | --- | --- |
| 345 | How secure is Taiwan? The view from Taipei | `success` | `approved` |
| 346 | A summer of AI summits reveals a widening US-China divide | `success` | `approved` |
| 347 | Europe’s China Shock 2.0: Where does it go from here? | `success` | `approved` |
| 348 | Middle power AI agency: Preserving choice between the United States and China | `success` | `approved` |

结论：

- Brookings 历史待复核样本已先完成 4 篇批准。
- Brookings 剩余待复核样本为 349、350、351、352、353、378，共 6 篇。
- 批准前备份已保存到
  `docs/backups/20260921-brookings-345-348-approved/reports-345-348-before-approval.json`。

### 2026-09-21 Brookings 第二批历史样本复核通过

复核结果：

| 报告 ID | 标题 | AI 状态 | 复核状态 |
| --- | --- | --- | --- |
| 349 | Turning the tide: China seeks to set the rules at sea | `success` | `approved` |
| 350 | What’s lost when reporters leave China? | `success` | `approved` |
| 351 | Why Beijing isn’t taking the bait with Trump | `success` | `approved` |
| 352 | The hidden tradeoffs of using Trump’s tariffs as leverage with China | `success` | `approved` |

结论：

- Brookings 历史待复核样本已累计完成 8 篇批准。
- Brookings 剩余待复核样本为 353、378，共 2 篇。
- 批准前备份已保存到
  `docs/backups/20260921-brookings-349-352-approved/reports-349-352-before-approval.json`。

### 2026-09-21 Brookings 第三批历史样本复核通过

复核结果：

| 报告 ID | 标题 | AI 状态 | 复核状态 |
| --- | --- | --- | --- |
| 353 | Advancing human control of military AI | `success` | `approved` |
| 378 | How strong is the Chinese Communist Party’s hold on power? | `success` | `approved` |

结论：

- Brookings 历史待复核样本已累计完成 10 篇批准。
- Brookings 当前 `pending_review` 历史样本清零。
- 批准前备份已保存到
  `docs/backups/20260921-brookings-353-378-approved/reports-353-378-before-approval.json`。

### 2026-09-21 CFR 历史样本复核通过

复核结果：

| 报告 ID | 标题 | 文档形态 | 页数 | AI 状态 | 复核状态 |
| --- | --- | --- | ---: | --- | --- |
| 365 | Out of Ammo: A Two-Year Sprint to Rebuild the American Arsenal and Deter China | `pdf` | 20 | `success` | `approved` |
| 366 | The Pharma Choke Point | `pdf` | 96 | `success` | `approved` |
| 367 | Leapfrogging China’s Critical Minerals Dominance | `pdf` | 50 | `success` | `approved` |
| 368 | The Next Taiwan Crisis Won’t Be Like the Last | `pdf` | 20 | `success` | `approved` |
| 379 | The Cyber Gap | `pdf` | 43 | `success` | `approved` |

结论：

- CFR 历史待复核样本已累计完成 5 篇批准。
- CFR 当前 `pending_review` 历史样本清零。
- 批准前备份已保存到
  `docs/backups/20260921-cfr-365-368-379-approved/reports-365-368-379-before-approval.json`。

### 2026-09-21 PIIE 历史样本复核通过

复核结果：

| 报告 ID | 标题 | 文档形态 | 页数 | AI 状态 | 复核状态 |
| --- | --- | --- | ---: | --- | --- |
| 370 | China's economic security growth model and implications for the US-China security dilemma | `pdf` | 56 | `success` | `approved` |
| 371 | How did Trump’s 2025 trade war affect the decoupling of US-China supply chains? | `pdf` | 37 | `success` | `approved` |
| 372 | US-China cooperative interdependence: Opportunities and obstacles | `pdf` | 73 | `success` | `approved` |
| 373 | Made with China: Global supply chains and the limits of US decoupling | `pdf` | 45 | `success` | `approved` |

结论：

- PIIE 历史待复核样本已累计完成 4 篇批准。
- PIIE 当前 `pending_review` 历史样本清零。
- 批准前备份已保存到
  `docs/backups/20260921-piie-370-373-approved/reports-370-373-before-approval.json`。

### 2026-09-21 CSIS 主入口样本批准与 RSS 历史样本清理

处理结果：

| 对象 | 处理 | 说明 |
| --- | --- | --- |
| 报告 343 | `approved` | CSIS 主入口 `/analysis` PDF 样本，32 页，AI 输出完整，前端复核通过 |
| 报告 261-270 | `rejected` | CSIS RSS 返回的 2016 年旧活动页，非长篇研究报告，正文和 AI 输出过短 |
| 来源 53 | `is_active=false` | `https://www.csis.org/rss.xml` 停用，保留 CSIS 主入口 `/analysis` |

结论：

- CSIS 主入口当前已有 4 篇前端复核通过样本：343、383、385、386。
- CSIS RSS 历史旧活动页样本已全部拒绝，不再混入待复核队列。
- CSIS 当前 `pending_review` 历史样本清零。
- 处理前备份已保存到
  `docs/backups/20260921-csis-343-approve-rss-reject/reports-343-261-270-before-review.json`
  和
  `docs/backups/20260921-csis-343-approve-rss-reject/source-53-before-disable.json`。

### 2026-09-18 AEI 文档抽取修复跟进

本轮已对报告文档抽取逻辑做保守增强：

- 对允许网页长文兜底的来源，若报告页发现 PDF 但 PDF 页数不足或文本提取失败，可继续尝试从原始报告页抽取网页正文。
- 只有网页正文达到 `CRAWLER_MIN_WEB_ARTICLE_CONTENT_LENGTH` 门槛时，才作为 `web_article` 返回。
- 未发现 PDF 的原有网页长文兜底逻辑保持不变。
- 短 PDF 且网页正文也不足的样本仍保持失败，不放宽质量门槛。

验证结果：

- 相关单元测试和 ruff 检查通过。
- AEI 只读审计结果从 `document_ok=0/3` 改善为 `document_ok=1/3`。

样本结果：

| 样本 | 修复后结果 | 说明 |
| --- | --- | --- |
| Flipping the Script: How to Hold China's New Carriers at Risk | 失败 | 页面 `Download PDF` 链接为空；正文约 1307 字符，低于网页长文门槛 |
| Dataset: China Global Investment Tracker | 失败 | 跳转到专题页，不像单篇报告，未抽取到合格正文 |
| China's Outbound Investment Shrugs Off the Iran War | 通过 | PDF 仅 16 页，但网页正文约 53,498 字符，按 `web_article` 通过 |

结论：

- AEI 的长文兜底链路已具备试运行价值，但仍存在一定跳过率。
- 扩大到 10 条候选的只读审计中，AEI 有 7 条通过文档检查，均为网页长文，建议进入小批量入库试运行。
- 策略调整为 `pilot_crawl` + `web_article_allowed`，但仍建议每次最多保存 1 篇、默认不通知、AI 状态先设为 `skipped`。

### 2026-09-18 AEI 小批量真实入库试运行

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.pilot_crawl_sources --keys aei --max-saved 1 --max-candidates 10 --ai-status skipped
```

执行口径：

- 真实写入抓取运行记录。
- 最多保存 1 篇新报告。
- 默认不创建通知。
- 新报告 AI 状态设为 `skipped`，避免自动排队。

执行结果：

| 机构 | crawl_run_id | 发现候选 | 新增入库 | 主要结果 |
| --- | ---: | ---: | ---: | --- |
| AEI | 500 | 10 | 1 | 2 条文档获取失败；1 条网页长文成功入库 |

新增报告：

| 报告 ID | 标题 | 正文类型 | AI 状态 | 正文长度 |
| ---: | --- | --- | --- | ---: |
| 380 | China's Outbound Investment Shrugs Off the Iran War | `web_article` | `skipped` | 53,498 字符 |

结论：

- AEI 小批量入库试运行成功，长文兜底策略可以产出合格网页长文报告。
- 新报告默认未排 AI，建议先在前端复核报告 ID 380 的正文质量，再手动触发 AI 处理。
- 若 ID 380 的正文质量和后续 AI 成果通过人工复核，可继续对 AEI 执行下一轮每次 1 篇的小批量试运行。

### 2026-09-18 AEI 报告 380 AI 处理结果

处理对象：

- 报告 ID：380
- 标题：`China's Outbound Investment Shrugs Off the Iran War`
- 正文类型：`web_article`
- 正文长度：53,498 字符

处理过程：

- 初始 AI 状态为 `skipped`。
- 手动提交 AI 分块任务时，Celery 结果库出现重连失败；随后检查发现分块任务已实际执行完成。
- 报告 380 共完成 translation 分块 19 个、analysis 分块 4 个。
- 在确认全部分块成功后，手动运行本地 finalizer 完成最终汇总。

最终结果：

| 字段 | 结果 |
| --- | ---: |
| AI 状态 | `success` |
| 复核状态 | `pending_review` |
| 全文翻译长度 | 22,357 字符 |
| 主要观点长度 | 1,896 字符 |
| 深层研判长度 | 2,008 字符 |
| AI 生成时间 | 2026-09-18 05:48:18 |

结论：

- 主要观点和深层研判均达到目标字数区间。
- 该样本可进入前端人工复核。
- Celery 结果库重连失败当时阻断了继续扩大 AI 处理；后续定位结果见下节。

### 2026-09-18 Celery 本地命令环境排查结果

排查结论：

- Redis 服务本身可用，`127.0.0.1:6379/0` 和 `127.0.0.1:6379/1`
  均可连接。
- 本地直接运行 `poetry run ...` 会读取 `backend/.env` 中 Docker 网络使用的
  `redis` 主机名，导致 Celery broker / result backend 在 Windows 本地解析失败。
- 新增 `scripts/run-local-backend-command.ps1` 作为本地人工命令入口，统一注入
  `127.0.0.1` Redis 地址和指定 Celery 队列。

验证结果：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-local-backend-command.ps1 -Queue celery poetry run python ...
```

- 实际 broker：`redis://127.0.0.1:6379/0`
- 实际 result backend：`redis://127.0.0.1:6379/1`
- 实际队列：`celery`
- 零处理量任务：`report.enqueue_ai_chunk_tasks(report_limit=0, chunk_limit=0)`
- 任务结果：`SUCCESS`，返回 `[]`

结论：

- 先前重连失败的根因是本地命令入口读取了 Docker Redis 主机名，并非 Redis
  或 Celery result backend 本身不可用。
- 后续本地诊断、爬虫和 AI 运维命令应统一通过
  `scripts/run-local-backend-command.ps1` 执行。
- 可以恢复小批量 AI 队列验证，但仍建议每次只处理 1 篇报告。

### 2026-09-18 AEI 小批量 AI 队列验证结果

执行命令：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-local-backend-command.ps1 -Queue celery poetry run python -m app.scripts.pilot_crawl_sources --keys aei --max-saved 1 --max-candidates 15 --ai-status pending
```

抓取结果：

| 机构 | crawl_run_id | 发现候选 | 新增入库 | 主要结果 |
| --- | ---: | ---: | ---: | --- |
| AEI | 501 | 13 | 1 | 新增 1 篇网页长文报告，重复 2 篇，3 篇文档获取失败 |

新增报告：

| 报告 ID | 标题 | 正文类型 | 正文长度 |
| ---: | --- | --- | ---: |
| 381 | `Connected and Autonomous Cars: Security Risks from Chinese Components` | `web_article` | 30,223 字符 |

AI 队列验证结果：

| 字段 | 结果 |
| --- | ---: |
| AI 状态 | `success` |
| 复核状态 | `pending_review` |
| translation 分块 | 11 个，全部 `success` |
| analysis 分块 | 2 个，全部 `success` |
| 全文翻译长度 | 12,535 字符 |
| 主要观点长度 | 1,741 字符 |
| 深层研判长度 | 2,132 字符 |
| AI 生成时间 | 2026-09-18 06:41:57 |

结论：

- 本地包装脚本 + `celery` 队列可以支持真实 AI 分块任务投递、worker 消费和
  finalizer 汇总。
- 报告 381 的主要观点和深层研判均达到目标字数区间，可进入前端人工复核。
- AEI 可以继续采用“每次最多新增 1 篇、人工复核后再扩大”的节奏。

### 2026-09-18 AEI 报告 380/381 初步质量复核

复核对象：

| 报告 ID | 标题 |
| ---: | --- |
| 380 | `China's Outbound Investment Shrugs Off the Iran War` |
| 381 | `Connected and Autonomous Cars: Security Risks from Chinese Components` |

结构指标：

| 报告 ID | 部分 | 字符数 | 段落数 | 显式分论点编号 | 乱码替换符 |
| ---: | --- | ---: | ---: | ---: | ---: |
| 380 | 主要观点 | 1,896 | 4 | 0 | 0 |
| 380 | 深层研判 | 2,008 | 4 | 0 | 0 |
| 381 | 主要观点 | 1,741 | 4 | 0 | 0 |
| 381 | 深层研判 | 2,132 | 4 | 0 | 0 |

初步判断：

- 两篇报告的“主要观点”均处于 1500-2000 字目标区间。
- 两篇报告的“深层研判”均处于 2000-2500 字目标区间。
- 数据库文本未发现 `�` 替换字符；命令行片段显示乱码属于 PowerShell 输出编码问题，
  不作为正文质量问题。
- 当前 AI 成果虽然自然形成 4 个段落，但没有显式使用“一、二、三、四”等分论点编号
  或小标题，不完全贴合“4 个及以上分论点”的版式要求。

建议：

- 在前端人工复核报告 380、381 时，重点确认观点是否准确、翻译是否通顺、
  深层研判是否有独立分析增量。
- 已对 AI finalizer 提示词进行编号分论点优化，并用报告 381 重新生成样本对比；
  结果见下节。

### 2026-09-18 报告 381 编号分论点重生成验证

调整内容：

- `summary` 提示词要求显式使用“一、二、三、四”等中文编号组织
  4 个以上主要观点。
- `commentary` 提示词要求显式使用“一、二、三、四、五”等中文编号组织
  5 个以上深层研判分论点，以提高 2000-2500 字目标区间的稳定性。
- 长度重试提示同步要求保留中文编号分论点，禁止输出无编号连续段落。

验证过程：

- 已将报告 381 原始 AI 成果导出到
  `docs/backups/20260918-report-381-regenerate/report-381-ai-before-numbered-regenerate.json`。
- 第一次重跑 finalizer 时，`summary` 已生成 4 个编号分论点并达标；
  `commentary` 四次尝试仍低于 2000 字，未保存。
- 随后加强 `commentary` 提示词为 5 个以上编号分论点，再次运行 finalizer；
  finalizer 复用已达标的 `summary`，只补齐 `commentary`。

重生成结果：

| 字段 | 结果 |
| --- | ---: |
| AI 状态 | `success` |
| 全文翻译长度 | 12,535 字符 |
| 主要观点长度 | 1,583 字符 |
| 主要观点编号分论点 | 4 个 |
| 深层研判长度 | 2,192 字符 |
| 深层研判编号分论点 | 5 个 |
| AI 生成时间 | 2026-09-18 07:16:09 |

结论：

- 新提示词已能让报告 381 的“主要观点”和“深层研判”显式输出编号分论点。
- 主要观点和深层研判均达到目标字数区间。
- 新版 AI 成果已导出到
  `docs/backups/20260918-report-381-regenerate/report-381-ai-after-numbered-regenerate.json`，
  可与原稿对比复核。

### 2026-09-18 Brookings 报告 352 跨来源编号结构验证

验证对象：

| 报告 ID | 来源 | 标题 |
| ---: | --- | --- |
| 352 | Brookings | `The hidden tradeoffs of using Trump's tariffs as leverage with China` |

验证过程：

- 已将报告 352 原始 AI 成果导出到
  `docs/backups/20260918-report-352-regenerate/report-352-ai-before-numbered-regenerate.json`。
- 仅清空 `summary` / `commentary` 并将报告级 AI 状态置回 `processing`，
  保留已有 translation 和 analysis chunks，不重跑翻译分块。
- 使用新提示词运行 finalizer。第一次输出偏短，系统重试后自动扩写并通过长度校验。

重生成结果：

| 字段 | 结果 |
| --- | ---: |
| AI 状态 | `success` |
| 全文翻译长度 | 3,233 字符 |
| 主要观点长度 | 1,702 字符 |
| 主要观点编号分论点 | 4 个 |
| 深层研判长度 | 2,054 字符 |
| 深层研判编号分论点 | 5 个 |
| AI 生成时间 | 2026-09-18 07:24:09 |

结论：

- 新提示词在非 AEI 来源 Brookings 样本上同样能稳定产出显式编号分论点。
- 主要观点和深层研判均达到目标字数区间。
- 新版 AI 成果已导出到
  `docs/backups/20260918-report-352-regenerate/report-352-ai-after-numbered-regenerate.json`，
  可与原稿对比复核。

### 2026-09-27 RAND / Carnegie / Atlantic Council 老师重点名单只读审计

背景：

- 老师附件将 RAND、Carnegie Endowment、Atlantic Council 列为重点覆盖机构。
- 本轮只读审计不写数据库、不发通知、不调用 LLM，仅验证现有发现入口和文档提取质量。

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.audit_source_documents --keys rand,carnegie,atlantic_council --max-candidates 3 --discovery-timeout 90 --document-timeout 120
```

补充检查：

```powershell
cd backend
poetry run python -c "<只读检查 Atlantic Council RSS 前 5 条候选>"
poetry run python -c "<只读检查 Carnegie 候选网页是否可作为网页长文>"
```

运行结果：

| 来源 | key | rollout 状态 | 原始候选 | 去重候选 | 检查候选 | 文档通过 | 文档失败 | 主要结果 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| RAND Corporation | `rand` | `standard_review` | 33 | 33 | 3 | 2 | 1 | 可发现 20 页以上 PDF，当前适合进入人工小样本试写 |
| Carnegie Endowment | `carnegie` | `standard_review` | 1 | 1 | 1 | 0 | 1 | 召回涉华网页 `American Power: A View from China`，但当前文档服务要求 PDF，未通过 |
| Atlantic Council | `atlantic_council` | `standard_review` | - | - | - | - | - | website 来源缺专用解析器，主审计报 `当前尚未配置该 website 来源的专用解析器` |

RAND 抽样明细：

| 标题 | 文档结果 | 页数 | 说明 |
| --- | --- | ---: | --- |
| `Understanding Russia's Role in Latin America` | 通过 | 58 | PDF 可下载，文本约 171,828 字符 |
| `Patterns of Disconnection Among America's Youth` | 未通过 | 16 | PDF 页数不足 20 页，被正确拒绝 |
| `Artificial Superintelligence: U.S. Strategy for an Uncertain Future` | 通过 | 37 | PDF 可下载，文本约 96,809 字符 |

Carnegie 抽样明细：

| 标题 | 文档结果 | 说明 |
| --- | --- | --- |
| `American Power: A View from China` | 未通过 | 页面涉华，但当前 `fetch_report_document` 即使开启网页长文 fallback 仍返回“未发现 PDF 链接” |

Atlantic Council 补充 RSS 检查：

- RSS 可返回约 100 条候选。
- 前 5 条包含 dispatch、Fast Thinking、in-the-news、issue brief、UkraineAlert 博客等多种内容形态。
- RSS 噪声明显高于 RAND / Carnegie，若直接接入容易混入快评、转载、新闻引用、博客和活动型内容。
- 当前更适合先开发 website 报告页专用解析器，只保留 `/in-depth-research-reports/` 下的 report / issue brief 等重型研究成果，再做只读审计。

结论：

- RAND：通过只读审计的最低门槛，建议下一步经人工确认后用 `--allow-standard-review --max-saved 1 --ai-status skipped` 试写 1 篇，不直接升级为 `pilot_crawl`。
- Carnegie：来源价值高，但当前 PDF/网页长文提取链路不通过；需先确认是否允许其长网页研究成果入库，并修正文档服务对 Carnegie 页面正文的识别。
- Atlantic Council：不能直接进入试写；需先补专用解析器或专门入口过滤，避免 RSS 噪声污染正式报告库。
- 三个来源均保持 `standard_review`，不允许自动入库试运行。

### 2026-09-27 RAND 人工小样本试写

试写前备份：

- `docs/backups/20260927-rand-manual-sample/rand-before-sample.json`
- `docs/backups/20260927-rand-manual-sample/export_source_state.py`

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.pilot_crawl_sources --keys rand --allow-standard-review --max-saved 1 --max-candidates 5 --ai-status skipped
```

运行结果：

| 来源 | source_id | crawl_run_id | 检查候选 | 新增入库 | AI 状态 | 通知 |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| RAND Corporation | 7 | 702 | 5 | 1 | `skipped` | 未开启 |

新增报告：

| report_id | 标题 | 页数 | 文档形态 | review 状态 | 判断 |
| ---: | --- | ---: | --- | --- | --- |
| 436 | `Understanding Russia's Role in Latin America` | 58 | PDF | `pending_review` | PDF 与正文抽取合格，但标题和主题不明显涉华 |

试写后备份：

- `docs/backups/20260927-rand-manual-sample/rand-after-sample.json`

质量结论：

- 本轮证明 RAND website 入口能保存长 PDF，文档提取链路可用。
- 但本轮保存的第一篇报告主题偏向俄罗斯与拉美，未体现平台要求的“重磅涉华研究报告”。
- 这说明 RAND 当前发现顺序和入库前涉华过滤仍不够稳，不应升级为 `pilot_crawl`。
- 后续应先收紧 RAND 解析器或候选选择逻辑，例如优先从 China topic、标题/URL 含 China/Taiwan/Beijing 等显性信号的报告进入人工试写，再考虑继续样本验证。
- RAND 旧 RSS `https://www.rand.org/rss.xml` 仍处于 active 但返回 404；可在后续清理重复/失效 source 时停用，保留 `https://www.rand.org/pubs/new.xml`。

建议处理：

- 报告 436 已于 2026-09-27 按人工确认标记为 `rejected`，不进入 AI 生成。
- RAND 继续保持 `standard_review`。

### 2026-09-27 RAND 样本拒绝与涉华过滤修复

处理动作：

- 已备份 report 436 拒绝前状态：
  `docs/backups/20260927-rand-filter-reject-436/report-436-before-reject.json`
- 已通过 `report_service.update_report` 将 report 436 标记为 `rejected`，复核备注为：
  `RAND 人工小样本试写样本不明显涉华，暂不采用；后续需先收紧 RAND 涉华过滤/候选排序。`
- 已导出拒绝后状态：
  `docs/backups/20260927-rand-filter-reject-436/report-436-after-reject.json`

代码修复：

- `CORE_SITE_CONFIGS["rand"]` 增加 `require_china_signal=True`。
- `CORE_SITE_CONFIGS["rand"]` 增加 `require_china_signal_in_title_or_url=True`。
- RAND 通用列表页不再因为卡片正文、摘要或列表上下文零散出现 China/BRICS 而放行候选；候选标题或 URL 本身必须明确涉华。
- 新增测试覆盖 `Understanding Russia's Role in Latin America` 这类“正文零散提及中国但标题/URL 不涉华”的样本，确保不再进入 RAND 候选。

验证：

```powershell
cd backend
poetry run pytest tests/test_us_core_parser.py
poetry run pytest tests/test_crawler_service.py tests/test_pilot_crawl_sources.py tests/test_source_rollout_policy.py
```

结果：

- `tests/test_us_core_parser.py`：20 passed。
- `tests/test_crawler_service.py tests/test_pilot_crawl_sources.py tests/test_source_rollout_policy.py`：36 passed。

### 2026-09-27 RAND 涉华过滤修复后只读复审

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.audit_source_documents --keys rand --max-candidates 5 --discovery-timeout 90 --document-timeout 120
```

运行结果：

| 来源 | rollout 状态 | 原始候选 | 去重候选 | 检查候选 | 文档通过 | 文档失败 | 结论 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| RAND Corporation | `standard_review` | 8 | 8 | 5 | 4 | 1 | 候选显著收紧，前 5 条均为显性涉华标题 |

抽样明细：

| 标题 | 结果 | 页数 | 说明 |
| --- | --- | ---: | --- |
| `China's Strategic Petroleum Reserve as a Geoeconomic Tool` | 通过 | 23 | PDF 可下载，文本约 48,240 字符 |
| `Understanding China's Naval Maintenance Management` | 通过 | 71 | PDF 可下载，文本约 232,056 字符 |
| `AI Development in the United States and China: Evidence from a New Dataset of AI Developer Firms` | 通过 | 64 | PDF 可下载，文本约 131,174 字符 |
| `Exploring AI's Operational Implications in a Future U.S.-China Conflict: Initial Observations from the Camp(ai)gn Wargame` | 通过 | 40 | PDF 可下载，文本约 125,348 字符 |
| `After Annexation: How China Plans to Run Taiwan` | 未通过 | - | 外部出版页未发现 PDF 链接，被正确拒绝 |

与修复前对比：

- 修复前只读审计：33 条候选，前列混入 `Understanding Russia's Role in Latin America` 等不明显涉华报告。
- 修复后只读复审：8 条候选，抽查 5 条均为标题或 URL 显性涉华，其中 4 条通过 PDF/页数/文本检查。
- 修复后的 RAND 候选质量已明显改善，可进入第二次人工小样本试写。

建议：

- 可对 RAND 再执行一次 `--allow-standard-review --max-saved 1 --max-candidates 5 --ai-status skipped` 受控试写。
- 仍不直接升级为 `pilot_crawl`；至少需要第二次试写样本通过前端人工复核后再评估。

### 2026-09-30 RAND 二次只读复核与受控试写

执行计划：

- 先对 RAND 当前网站结果做只读复核，不写库。
- 只读复核通过后执行一次受控试写，限制 `--max-saved 1`，并使用 `--ai-status skipped` 避免自动触发 AI 生成。
- 写入后只读核验数据库记录，再决定是否更新 rollout 文档。

只读复核命令：

```powershell
cd backend
poetry run python -m app.scripts.audit_source_documents --keys rand --max-candidates 5 --discovery-timeout 90 --document-timeout 120
```

只读复核结果：

| 来源 | rollout 状态 | 原始候选 | 去重候选 | 检查候选 | 文档通过 | 文档失败 | 结论 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| RAND Corporation | `standard_review` | 9 | 9 | 5 | 5 | 0 | 当前候选均为显性涉华长篇 PDF，可进行第二次受控试写 |

抽样明细：

| 标题 | 结果 | 页数 | 说明 |
| --- | --- | ---: | --- |
| `The Scope and Nature of the U.S.-China Competition` | 通过 | 113 | PDF 可下载，文本约 320,311 字符 |
| `China's Strategic Petroleum Reserve as a Geoeconomic Tool` | 通过 | 23 | PDF 可下载，文本约 48,240 字符 |
| `Understanding China's Naval Maintenance Management` | 通过 | 71 | PDF 可下载，文本约 232,056 字符 |
| `AI Development in the United States and China: Evidence from a New Dataset of AI Developer Firms` | 通过 | 64 | PDF 可下载，文本约 131,174 字符 |
| `Exploring AI's Operational Implications in a Future U.S.-China Conflict: Initial Observations from the Camp(ai)gn Wargame` | 通过 | 40 | PDF 可下载，文本约 125,348 字符 |

受控试写命令：

```powershell
cd backend
poetry run python -m app.scripts.pilot_crawl_sources --keys rand --allow-standard-review --max-saved 1 --max-candidates 5 --ai-status skipped
```

受控试写结果：

| 来源 | source_id | crawl_run_id | 检查候选 | 新增入库 | AI 状态 | 通知 |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| RAND Corporation | 7 | 724 | 5 | 1 | `skipped` | 未开启 |

新增报告：

| report_id | 标题 | 页数 | 非空页 | 正文长度 | 文档形态 | review 状态 | 判断 |
| ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| 439 | `The Scope and Nature of the U.S.-China Competition` | 113 | 108 | 320,311 | PDF | `pending_review` | 标题显性涉华，PDF 与正文抽取合格，待前端人工复核 |

质量结论：

- RAND 涉华过滤修复后的候选质量稳定，二次试写未再保存不明显涉华报告。
- 本轮证明 RAND 当前解析器、PDF 提取和 20 页门槛可以覆盖高价值涉华长报告。
- 在 report 439 完成 AI 生成和人工复核前，RAND 仍保持 `standard_review`，不直接升级为 `pilot_crawl`。
- 当时下一步是先由前端人工复核 report 439 的主题相关性、PDF 链接、正文抽取完整性和展示效果；通过后再评估是否升级为每次最多新增 1 篇的小批量试运行。

### 2026-09-30 RAND AI 生成、人工复核与升级

AI 生成：

- 已对 report 439 执行报告 AI 生成。
- 任务分块总数 130 个，其中全文翻译 109 个、分析分块 21 个。
- 分块结果 130/130 完成，失败 0 个。
- 最终 `ai_status=success`。

成果质量抽查：

| 成果 | 长度 | 结构 | 判断 |
| --- | ---: | --- | --- |
| 全文翻译 | 115,462 字符 | 开头、中段、结尾连续，包含注释与参考文献、`第 113 页注释` | 可交付，术语可后续人工润色 |
| 主要观点 | 1,570 字符 | 4 个分论点 | 符合 1500-2000 字和 4 个以上分论点要求 |
| 深层研判 | 2,384 字符 | 5 个分论点 | 符合 2000-2500 字和 4 个以上分论点要求 |

人工复核：

- 已将 report 439 标记为 `approved`。
- 复核记录 ID：48。
- 复核意见：`RAND 二次受控试写样本已完成复核：PDF 113 页，正文抽取完整；AI 全文翻译、主要观点和深层研判均已生成，字数和分论点结构符合交付要求。翻译术语后续可人工润色，但不影响本轮自动化流程验收，同意通过。`

升级处理：

- RAND 已完成“只读复核 -> 受控试写 -> AI 生成 -> 人工通过”的完整闭环。
- `source_rollout_policy.py` 已将 `rand` 纳入 `PILOT_CRAWL_KEYS`。
- RAND 文档策略保持 `pdf_20_page_required`，不允许网页长文特例。
- 后续仍应采用每次最多新增 1 篇、前端人工复核后再扩大的保守节奏。

### 2026-10-01 RAND 正式 pilot_crawl 试抓

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.pilot_crawl_sources --keys rand --max-saved 1 --max-candidates 5 --ai-status skipped
```

运行结果：

| 来源 | source_id | crawl_run_id | 检查候选 | 新增入库 | AI 状态 | 说明 |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| RAND Corporation | 7 | 725 | 5 | 0 | `skipped` | 不带 `--allow-standard-review` 成功通过策略守卫；5 条候选均为重复 |

候选明细：

| 标题 | 状态 | 跳过原因 |
| --- | --- | --- |
| `The Scope and Nature of the U.S.-China Competition` | `skipped` | `duplicate_existing` |
| `China's Strategic Petroleum Reserve as a Geoeconomic Tool` | `skipped` | `duplicate_existing` |
| `Understanding China's Naval Maintenance Management` | `skipped` | `duplicate_existing` |
| `AI Development in the United States and China: Evidence from a New Dataset of AI Developer Firms` | `skipped` | `duplicate_existing` |
| `Exploring AI's Operational Implications in a Future U.S.-China Conflict: Initial Observations from the Camp(ai)gn Wargame` | `skipped` | `duplicate_existing` |

结论：

- RAND 正式 `pilot_crawl` 链路已验证生效。
- 本轮 `saved_count=0` 是去重逻辑按预期工作，不是解析或策略失败。
- 后续可将 RAND 纳入常规小批量试运行观察，继续限制每次最多新增 1 篇并要求前端人工复核。

### 2026-10-01 Carnegie PDF 识别修复与只读复核

背景：

- 2026-09-27 只读审计中，Carnegie 只召回 `American Power: A View from China` 网页，未发现 PDF，暂不进入试写。
- 本轮重新审计时，Carnegie 官网可召回涉华核议题长报告，但初始结果为网页长文，提示 PDF 链接识别仍需修复。

问题定位：

- 样本页面存在 `Full Text (PDF)` 链接：
  `https://assets.carnegieendowment.org/files/Zhao_Nuclear%20Knot.pdf`
- `extract_report_pdf_url` 已给 `full text` 计分，但 `has_report_intent` 未包含 `full text`，导致该 PDF 被过滤。
- PDF 直链验证结果为 39 页、38 个有效文本页，正文约 117,144 字符，符合 20 页 PDF 门槛。

代码修复：

- `extract_report_pdf_url` 将 `full text` 纳入明确报告 PDF 意图。
- 仍要求目标链接本身包含 `.pdf`，避免把正文中的普通外部 `Full Text` 链接误判为报告 PDF。
- 新增 `tests/test_content_extractor.py` 覆盖：
  - `Full Text (PDF)` 链接可被识别；
  - 非 PDF 的 `Full Text` 链接不会被误判。

修复后只读复核命令：

```powershell
cd backend
poetry run python -m app.scripts.audit_source_documents --keys carnegie --max-candidates 5 --discovery-timeout 90 --document-timeout 120
```

运行结果：

| 来源 | rollout 状态 | 原始候选 | 去重候选 | 检查候选 | 文档通过 | 文档失败 | 结论 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Carnegie Endowment | `standard_review` | 1 | 1 | 1 | 1 | 0 | PDF 识别修复后，样本符合 20 页长报告门槛 |

抽样明细：

| 标题 | 结果 | 文档形态 | 页数 | 说明 |
| --- | --- | --- | ---: | --- |
| `Untangling the Nuclear Knot: A Constructive Agenda for Managing China's Nuclear Relations with the United States and Its Allies` | 通过 | PDF | 39 | PDF 可下载，文本约 117,144 字符 |

验证：

```powershell
cd backend
poetry run pytest tests/test_content_extractor.py tests/test_report_document_service.py
poetry run ruff check app/services/crawler/content_extractor.py tests/test_content_extractor.py
```

结果：

- `tests/test_content_extractor.py tests/test_report_document_service.py`：8 passed。
- `ruff check`：All checks passed。

建议：

- Carnegie 继续保持 `standard_review`，暂不升级。
- 后续已完成一次受控试写、AI 生成和人工复核通过。
- 是否将 Carnegie 升级为 `pilot_crawl` 仍需单独确认。

### 2026-10-01 Carnegie 受控试写

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.pilot_crawl_sources --keys carnegie --allow-standard-review --max-saved 1 --max-candidates 5 --ai-status skipped
```

运行结果：

| 来源 | source_id | crawl_run_id | 检查候选 | 新增入库 | AI 状态 | 通知 |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| Carnegie Endowment | 8 | 726 | 1 | 1 | 入库 `skipped`；后续 `success` | 未开启 |

新增报告：

| report_id | 标题 | 页数 | 非空页 | 正文长度 | 文档形态 | review 状态 | 判断 |
| ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| 440 | `Untangling the Nuclear Knot: A Constructive Agenda for Managing China's Nuclear Relations with the United States and Its Allies` | 39 | 38 | 117,144 | PDF | `approved` | PDF 与正文抽取合格，主题显性涉华，AI 成果已通过复核 |

内容抽查：

- 标题无替换乱码，正文无替换乱码。
- 正文开头包含封面、标题、作者、目录；正文尾部包含注释与参考文献。
- 正文中 `China` 约 250 次，`nuclear` 约 404 次，主题相关性强。
- PDF 链接为 `https://assets.carnegieendowment.org/files/Zhao_Nuclear%20Knot.pdf`。

AI 与人工复核：

- 已对 report 440 触发 AI 生成，48 个分块全部完成，失败 0 个。
- 生成全文翻译约 39,734 字符，主要观点约 1,577 字符，深层研判约 2,347 字符。
- 主要观点包含 4 个分论点，深层研判包含 5 个分论点，导出 Markdown 和 Word 检查通过。
- report 440 已标记为 `approved`，复核事件 id 49；复核意见记录参考文献、URL 和机构地址保留英文较多，可后续人工润色，但不影响本轮自动化流程验收。

质量结论：

- Carnegie 受控试写成功，证明修复后的 PDF 识别和正文抽取链路可用于正式长报告。
- Carnegie 已完成“只读复核 -> 受控试写 -> AI 生成 -> 人工通过”的完整闭环。
- 代码 rollout 已升级为 `pilot_crawl`，文档策略保持 `pdf_20_page_required`。
- 升级后仍建议保持每次最多新增 1 篇和前端人工复核，不扩大抓取规模。

### 2026-10-01 Carnegie pilot_crawl 正式试抓

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.pilot_crawl_sources --keys carnegie --max-saved 1 --max-candidates 5 --ai-status skipped
```

运行结果：

| 来源 | source_id | crawl_run_id | 检查候选 | 新增入库 | 跳过原因 |
| --- | ---: | ---: | ---: | ---: | --- |
| Carnegie Endowment | 8 | 727 | 1 | 0 | 唯一候选已作为 report 440 入库，按 `duplicate_existing` 跳过 |

判断：

- Carnegie 已能不带 `--allow-standard-review` 通过 `pilot_crawl` 准入校验并完成正式试抓。
- 升级后策略确认为 `pilot_crawl` + `pdf_20_page_required`。
- 本轮没有新增报告并非异常，而是去重逻辑按预期生效。
- 后续仍保持每次最多新增 1 篇、AI 后前端人工复核的保守节奏。

### 2026-10-01 Atlantic Council website 解析器修复与只读复核

背景：

- 2026-09-27 老师重点名单只读审计中，Atlantic Council website 来源缺少专用解析器，主审计返回 `discovery_error`。
- RSS 可返回较多候选，但混有新闻、博客、活动、快评和转载信息，不适合直接进入正式报告库。
- 本轮目标是先修复 website 报告入口解析与文档提取，不写数据库、不触发 AI、不升级 rollout。

处理：

- 已将 Atlantic Council 接入 `CoreSiteConfig` 通用解析器。
- 发现入口包含：
  - `https://www.atlanticcouncil.org/region/china/`
  - `https://www.atlanticcouncil.org/in-depth-research-reports/`
  - `https://www.atlanticcouncil.org/content-series/atlantic-council-strategy-paper-series/`
- 候选 URL 限定为：
  - `/in-depth-research-reports/report/`
  - `/in-depth-research-reports/issue-brief/`
  - `/content-series/atlantic-council-strategy-paper-series/`
- 新增单元测试覆盖中国专题页报告卡片解析，以及普通报告列表对无涉华信号候选的过滤。

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.audit_source_documents --keys atlantic_council --max-candidates 5 --discovery-timeout 90 --document-timeout 120
```

运行结果：

| 来源 | key | rollout 状态 | 原始候选 | 去重候选 | 检查候选 | 文档通过 | 文档失败 | 文档策略 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Atlantic Council | `atlantic_council` | `standard_review` | 2 | 2 | 2 | 1 | 1 | `pdf_20_page_required` |

抽样明细：

| 标题 | 文档结果 | 文档形态 | 页数 | 正文长度 | 说明 |
| --- | --- | --- | ---: | ---: | --- |
| `Technology and the Global South: A US strategy for competitiveness` | 未通过 | 网页长报告 | - | - | 页面未发现 PDF 链接，按当前 PDF 策略拒绝 |
| `Building a multilateral cognitive warfare defense network: A collaborative framework for the United States, Japan, and Taiwan` | 通过 | PDF | 24 | 76,376 | PDF 链接可识别并成功抽取正文 |

质量结论：

- Atlantic Council website 解析器已修复，主审计状态从 `discovery_error` 变为 `ok`。
- 当前至少已有 1 篇 20 页以上 PDF 样本通过，说明报告页 PDF 链接识别和正文抽取链路可用。
- Atlantic Council 继续保持 `standard_review`，不直接升级。
- 是否允许无 PDF 的网页长报告作为 `web_article` 入库需单独确认；未确认前继续保持 `pdf_20_page_required`。
- 后续已执行一次 `--allow-standard-review --max-saved 1 --max-candidates 5 --ai-status skipped` 受控试写，优先验证通过的 PDF 样本。

### 2026-10-01 Atlantic Council 受控试写

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.pilot_crawl_sources --keys atlantic_council --allow-standard-review --max-saved 1 --max-candidates 5 --ai-status skipped
```

运行结果：

| 来源 | source_id | crawl_run_id | 检查候选 | 新增入库 | AI 状态 | 通知 |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| Atlantic Council | 9 | 728 | 2 | 1 | 入库 `skipped`；后续 `success` | 未开启 |

新增报告：

| report_id | 标题 | 页数 | 非空页 | 正文长度 | 文档形态 | review 状态 | 判断 |
| ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| 441 | `Building a multilateral cognitive warfare defense network: A collaborative framework for the United States, Japan, and Taiwan` | 24 | 24 | 76,376 | PDF | `approved` | PDF 与正文抽取合格，AI 成果已通过复核 |

跳过候选：

| 标题 | 跳过原因 |
| --- | --- |
| `Technology and the Global South: A US strategy for competitiveness` | 页面未发现 PDF 链接；按当前 `pdf_20_page_required` 策略拒绝 |

内容抽查：

- 正文无替换乱码。
- 正文中 `China` 约 68 次，`Chinese` 约 29 次，`Taiwan` 约 143 次，`Japan` 约 126 次，`cognitive` 约 75 次，主题相关性较强。
- PDF 链接为 `https://www.atlanticcouncil.org/wp-content/uploads/2026/09/Building-a-multilateral-cognitive-warfare-defense-network-A-collaborative-framework-for-the-United-States-Japan-and-Taiwan.pdf`。

AI 生成：

- 已对 report 441 触发 AI 生成，31 个分块全部完成，失败 0 个。
- 生成全文翻译约 28,128 字符，主要观点约 1,614 字符，深层研判约 2,196 字符。
- 主要观点包含 4 个分论点，深层研判包含 5 个分论点，导出 Markdown 和 Word 检查通过。
- report 441 已标记为 `approved`，复核事件 id 50。
- 复核意见记录报告主题涉中美日台认知战防御网络，涉华相关性明确；翻译术语后续可人工润色，但不影响本轮自动化流程验收。

质量结论：

- Atlantic Council 受控试写成功，证明 website 解析器、PDF 链接识别和正文抽取链路可用于正式长报告。
- Atlantic Council 已完成“解析器修复 -> 只读复核 -> 受控试写 -> AI 生成 -> 人工通过”的完整闭环。
- Atlantic Council 继续保持 `standard_review`，不直接升级。
- 第二次受控试写已执行但无新增，说明当前发现入口下可保存 PDF 样本不足，暂不建议直接升级为 `pilot_crawl`。
- 是否允许无 PDF 的网页长报告作为 `web_article` 入库仍需单独确认。

### 2026-10-01 Atlantic Council 第二次受控试写

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.pilot_crawl_sources --keys atlantic_council --allow-standard-review --max-saved 1 --max-candidates 10 --ai-status skipped
```

运行结果：

| 来源 | source_id | crawl_run_id | 检查候选 | 新增入库 | 跳过原因 |
| --- | ---: | ---: | ---: | ---: | --- |
| Atlantic Council | 9 | 729 | 2 | 0 | report 441 已入库重复 1 条；无 PDF 网页长报告失败 1 条 |

候选结果：

| 标题 | 结果 |
| --- | --- |
| `Building a multilateral cognitive warfare defense network: A collaborative framework for the United States, Japan, and Taiwan` | 已作为 report 441 入库，按 `duplicate_existing` 跳过 |
| `Technology and the Global South: A US strategy for competitiveness` | 页面未发现 PDF 链接，按当前 `pdf_20_page_required` 策略拒绝 |

质量结论：

- 第二次受控试写验证了 Atlantic Council 的去重和 PDF 门槛仍按预期生效。
- 试写前后 `source_id=9` 报告清单均只有 report 441，没有误入库。
- 当前解析入口下不足以产生第二篇可保存 PDF 样本。
- 下一步应优先扩展 Atlantic Council PDF 报告发现入口，或单独确认是否允许无 PDF 的网页长报告按 `web_article` 入库。

### 2026-10-01 Atlantic Council PDF 发现入口扩展

处理：

- 新增 `Global China Hub publications` 入口。
- 新增 `content-type/in-depth-research-reports` 入口及已验证能产生涉华 PDF 样本的分页。
- Atlantic Council 候选改为要求标题或 URL 自身具备 China / Chinese / Taiwan / East Asia / Northeast Asia 等涉华或周边地区信号，避免只因列表页上下文混入无关 PDF。
- 新增测试覆盖：
  - `East Asia` / `Northeast Asia` 作为周边地区信号；
  - `Global China Hub` 报告卡片解析；
  - Atlantic Council 配置包含已验证的 PDF 发现入口。

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.audit_source_documents --keys atlantic_council --max-candidates 10 --discovery-timeout 120 --document-timeout 150
```

运行结果：

| 来源 | key | rollout 状态 | 原始候选 | 去重候选 | 检查候选 | 文档通过 | 文档失败 | 文档策略 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Atlantic Council | `atlantic_council` | `standard_review` | 8 | 8 | 8 | 3 | 5 | `pdf_20_page_required` |

通过样本：

| 标题 | 文档形态 | 页数 | 正文长度 | 说明 |
| --- | --- | ---: | ---: | --- |
| `Building a multilateral cognitive warfare defense network: A collaborative framework for the United States, Japan, and Taiwan` | PDF | 24 | 76,376 | 已入库为 report 441 |
| `Preparing for and countering limited nuclear attacks in East Asia: Guardian Tiger III` | PDF | 44 | 141,021 | 新增可试写样本 |
| `Balancing openness and control: Cross-border health data and AI governance in China` | PDF | 38 | 178,890 | 新增可试写样本 |

主要失败样本：

| 标题 | 原因 |
| --- | --- |
| `Beijing pressures Taiwan’s remaining diplomatic partners. Here’s what the US should do in response` | 页面未发现 PDF 链接 |
| `After Maduro: Latin America’s policy community reassesses the US-China balance` | 页面未发现 PDF 链接 |
| `Chinese mining in West Africa: Responding to the environmental and social impacts` | PDF 10 页，低于 20 页门槛 |
| `The case for a US Northeast Asia Command` | 页面未发现 PDF 链接 |
| `To stop Chinese dual-use battery dominance, the United States and South Korea need to team up` | 页面未发现 PDF 链接 |

质量结论：

- 扩展后的发现入口已经能提供第二篇和第三篇可保存 PDF 样本。
- 严格过滤后不再保留标题和 URL 均无涉华/周边信号的 `Financing the end of the digital divide`。
- Atlantic Council 继续保持 `standard_review`，不直接升级。
- 后续已执行一次扩展入口后的受控试写，新增 report 442。
- 是否允许无 PDF 的网页长报告作为 `web_article` 入库仍需单独确认。

### 2026-10-01 Atlantic Council 扩展入口后受控试写

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.pilot_crawl_sources --keys atlantic_council --allow-standard-review --max-saved 1 --max-candidates 10 --ai-status skipped
```

运行结果：

| 来源 | source_id | crawl_run_id | 检查候选 | 新增入库 | AI 状态 | 通知 |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| Atlantic Council | 9 | 730 | 8 | 1 | `skipped` | 未开启 |

新增报告：

| report_id | 标题 | 页数 | 非空页 | 正文长度 | 文档形态 | review 状态 | 判断 |
| ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| 442 | `Balancing openness and control: Cross-border health data and AI governance in China` | 38 | 38 | 178,890 | PDF | `approved` | PDF 与正文抽取合格，主题显性涉华，AI 成果已通过复核 |

跳过候选：

| 标题 | 结果 |
| --- | --- |
| `Building a multilateral cognitive warfare defense network: A collaborative framework for the United States, Japan, and Taiwan` | 已作为 report 441 入库，按 `duplicate_existing` 跳过 |
| `Preparing for and countering limited nuclear attacks in East Asia: Guardian Tiger III` | 已作为历史 report 344 入库，按 `duplicate_existing` 跳过 |
| 其他 3 条候选 | 页面未发现 PDF 或 PDF 低于 20 页门槛 |

内容抽查：

- 正文无替换乱码。
- 正文中 `China` 约 432 次，`Chinese` 约 56 次，`AI` / `artificial intelligence` 约 171 次，`data` 约 763 次，`health` 约 256 次，主题相关性强。
- PDF 链接为 `https://www.atlanticcouncil.org/wp-content/uploads/2026/06/cross-border-health-data-ai-governance-china.pdf`。

质量结论：

- 扩展入口后的受控试写成功，新增样本符合 20 页 PDF 门槛。
- Atlantic Council 继续保持 `standard_review`，不直接升级。
- 后续已按用户授权触发 report 442 AI 生成并完成前端复核，已标记为 `approved`。
- Guardian Tiger III 已在历史库中存在；后续已单独复核 report 344 并标记为 `approved`。

### 2026-10-01 Atlantic Council report 442 AI 生成

执行说明：

- 已获得用户明确授权：将 report 442 全文发送给当前后端配置的 LLM 服务进行 AI 生成。
- 生成前已备份 report 442 数据库快照和相关文档到 `.codex-backups/step23-report442-ai-20261001-190000/`。
- 采用项目现有分块链路：`prepare_report_ai_chunks` -> `run_report_ai_chunk` -> `run_report_ai_finalization`。

运行结果：

| report_id | AI 分块 | 分块结果 | AI 状态 | review 状态 | 生成时间 |
| ---: | ---: | --- | --- | --- | --- |
| 442 | 73 | 73 个成功，0 个失败 | `success` | `approved` | `2026-10-01 10:10:06` |

交付物质量：

| 字段 | 长度 | 分论点 | 判断 |
| --- | ---: | ---: | --- |
| 全文翻译稿 | 70,107 字符 | - | 已生成，前端复核通过 |
| 主要观点 | 1,697 字符 | 4 | 符合 1500-2000 字、4 个及以上分论点口径 |
| 深层研判 | 2,088 字符 | 5 | 符合 2000-2500 字、4 个及以上分论点口径 |

异常与恢复：

- `chunk_id=3491` 普通重试后仍因译文长度不足失败。
- 检查该分块后确认其内容为正文加脚注，约 2,983 个字符，不是乱码或无关文本。
- 后续使用同一 LLM 服务按“逐段完整翻译并保留脚注、链接”的严格提示恢复该单块，恢复译文约 1,511 字符。
- 恢复后整篇 finalizer 成功，Markdown、Word 和质量检查文件已导出到 `.codex-backups/step23-report442-ai-20261001-190000/`。

质量结论：

- 后续已完成前端复核并标记为 `approved`，详见下一节。

### 2026-10-01 Atlantic Council report 442 前端复核通过

复核结果：

| 检查项 | 结果 |
| --- | --- |
| 前端报告页 | `/reports?report_id=442` 返回 200 |
| 详情接口 | report 442 可读取，`ai_status=success` |
| 列表检索 | `keyword=442` 可检索到 1 条 |
| PDF 元数据 | 38 页，38 个非空页，官方 PDF 链接 |
| AI 进度 | 73 个分块全部完成，失败 0 个 |
| Markdown 导出 | 200，包含全文翻译稿、主要观点、深层研判 |
| Word 导出 | 200，导出文件约 178,097 字节 |

批准记录：

- 已将 report 442 的复核状态从 `pending_review` 更新为 `approved`。
- 复核事件 id 51，复核人 `admin@thinktank.com`。
- 复核意见记录：报告详情接口、报告列表检索、PDF 元数据、正文完整性、AI 翻译稿、主要观点、深层研判及 Markdown/Word 导出均已检查；主要观点 1,697 字符/4 个分论点，深层研判 2,088 字符/5 个分论点；仍建议后续人工细读术语和脚注翻译。
- 批准前后快照与复核检查结果已保存至 `.codex-backups/step24-report442-review-approve-20261001-191500/`。

质量结论：

- report 442 已完成“扩展入口 -> 受控试写 -> AI 生成 -> 前端复核通过”的完整闭环。
- 后续已按用户确认将 Atlantic Council 升级为 `pilot_crawl`，详见下一节。

### 2026-10-01 Atlantic Council 升级为 pilot_crawl

处理：

| 来源 | 原 rollout | 新 rollout | 文档策略 | 运行节奏 |
| --- | --- | --- | --- | --- |
| Atlantic Council | `standard_review` | `pilot_crawl` | `pdf_20_page_required` | 每次最多新增 1 篇，AI 成功后前端人工复核 |

升级依据：

- report 441 已完成“解析器修复 -> 只读复核 -> 受控试写 -> AI 生成 -> 前端复核通过”的完整闭环。
- report 442 已完成“扩展入口 -> 受控试写 -> AI 生成 -> 前端复核通过”的完整闭环。
- 扩展后的 PDF 发现入口能提供 20 页以上、主题显性涉华或周边地区相关的长报告样本。
- 代码策略已将 `atlantic_council` 加入 `PILOT_CRAWL_KEYS`；文档策略继续保持 `pdf_20_page_required`，不放开无 PDF 网页长报告入库。

质量结论：

- Atlantic Council 已满足进入保守 `pilot_crawl` 的最低样本闭环要求。
- 升级后仍应重点观察重复入库、PDF 获取失败、短 PDF 跳过和无 PDF 网页报告跳过情况。
- 后续不扩大单次抓取规模，仍保持每次最多新增 1 篇和人工复核。

### 2026-10-01 Atlantic Council pilot_crawl 正式试抓

执行命令：

```powershell
cd backend
poetry run python -m app.scripts.pilot_crawl_sources --keys atlantic_council --max-saved 1 --max-candidates 10 --ai-status skipped
```

运行结果：

| 来源 | source_id | crawl_run_id | 检查候选 | 新增入库 | AI 状态 | 说明 |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| Atlantic Council | 9 | 733 | 8 | 0 | `skipped` | 未使用 `--allow-standard-review`，策略守卫已放行 |

候选处理：

| 类型 | 数量 | 说明 |
| --- | ---: | --- |
| 已入库重复 | 3 | 包括 report 441、report 442 和历史 report 344 对应报告 |
| PDF 获取/页数/文本检查失败 | 5 | 页面未发现 PDF 或 PDF 低于 20 页门槛 |
| 新增入库 | 0 | 去重与 PDF 门槛按预期生效 |

质量结论：

- Atlantic Council 已能不带 `--allow-standard-review` 通过 `pilot_crawl` 准入校验并完成正式试抓。
- 升级后策略确认为 `pilot_crawl` + `pdf_20_page_required`。
- 后续仍保持每次最多新增 1 篇和人工复核，重点观察重复入库、PDF 获取失败和短 PDF 跳过原因。

### 2026-10-01 Atlantic Council report 344 前端复核通过

复核对象：

| report_id | 标题 | 页数 | 非空页 | 正文长度 | 文档形态 | review 状态 |
| ---: | --- | ---: | ---: | ---: | --- | --- |
| 344 | `Preparing for and countering limited nuclear attacks in East Asia: Guardian Tiger III` | 44 | 44 | 141,021 | PDF | `approved` |

复核结果：

| 检查项 | 结果 |
| --- | --- |
| 前端报告页 | `/reports?report_id=344` 返回 200 |
| 详情接口 | report 344 可读取，`ai_status=success` |
| 列表检索 | `keyword=344` 可检索到 1 条 |
| PDF 元数据 | 44 页，44 个非空页，官方 PDF 链接 |
| AI 进度 | 38 个分块全部完成，失败 0 个 |
| Markdown 导出 | 200，包含全文翻译稿、主要观点、深层研判 |
| Word 导出 | 200，导出文件约 155,045 字节 |

交付物质量：

| 字段 | 长度 | 分论点 | 判断 |
| --- | ---: | ---: | --- |
| 全文翻译稿 | 54,002 字符 | - | 已生成，前端复核通过 |
| 主要观点 | 1,688 字符 | 4 | 符合 1500-2000 字和 4 个及以上分论点口径 |
| 深层研判 | 2,070 字符 | 4 | 符合 2000-2500 字和 4 个及以上分论点口径 |

批准记录：

- 已将 report 344 的复核状态从 `pending_review` 更新为 `approved`。
- 复核事件 id 52，复核人 `admin@thinktank.com`。
- 复核意见记录：Guardian Tiger III PDF 元数据、正文完整性、AI 分块进度、全文翻译稿、主要观点、深层研判及 Markdown/Word 导出均已检查；报告主题为东亚有限核攻击准备与应对，涉及中国、朝鲜半岛、日本、美国延伸威慑等区域安全议题，可纳入涉华及周边安全研究库。
- 批准前后快照与复核检查结果已保存至 `.codex-backups/step26-report344-review-approve-20261001-213000/`。

质量结论：

- report 344 已完成历史样本补复核。
- Atlantic Council 当前已有 report 344、441、442 三篇复核通过样本，后续仍保持 `pilot_crawl` + `pdf_20_page_required`，每次最多新增 1 篇并人工复核。

### 2026-10-01 Atlantic Council 无 PDF 候选发现阶段预检

处理内容：

- 为 Atlantic Council website 发现链路增加详情页 PDF 链接预检。
- 预检只判断报告详情页是否存在 PDF 链接，不替代最终 PDF 下载、正文抽取和 20 页门槛。
- 对预检确认无 PDF 的候选，直接在候选表中标记为 `未发现 PDF 链接`，错误摘要记录 `发现阶段预检：报告详情页中未发现 PDF 链接。`
- 对预检发现 PDF 链接的候选，先保存候选 `pdf_url`，随后仍进入正式文档检查；短 PDF 继续由 `PDF 页数不足` 规则识别。

验证命令：

```powershell
cd backend
poetry run python -m app.scripts.pilot_crawl_sources --keys atlantic_council --max-saved 1 --max-candidates 8 --ai-status skipped
```

验证结果：

| 来源 | source_id | crawl_run_id | 发现候选 | 新增入库 | AI 状态 |
| --- | ---: | ---: | ---: | ---: | --- |
| Atlantic Council | 9 | 735 | 8 | 0 | `skipped` |

候选处理：

| 类型 | 数量 | 说明 |
| --- | ---: | --- |
| 已入库重复 | 3 | 预检保留 PDF 链接，随后按已入库重复跳过 |
| 未发现 PDF 链接 | 4 | 发现阶段预检确认详情页无 PDF，未进入 PDF 下载/抽取 |
| PDF 页数不足 | 1 | 预检发现 PDF 链接，正式文档检查识别为 10 页，低于 20 页门槛 |

质量结论：

- Atlantic Council 候选展示已从笼统 `PDF 获取或页数/文本检查失败` 拆分为可解释的无 PDF、短 PDF 和重复候选。
- 预检降低了无 PDF 页面进入后续 PDF 下载/抽取链路造成的噪声，但仍保留候选记录，便于老师复查来源质量。
- `pdf_20_page_required` 文档策略保持不变，不放开无 PDF 网页长文入库。

## 下一步建议

1. Brookings、Carnegie、CFR、CSIS、PIIE、AEI 已完成历史样本清理或阶段验收，继续维持每次最多新增 1 篇的小批量试运行。
2. 新增样本继续坚持 AI 成功后前端人工复核；未通过样本进入 `needs_rerun`、补抓或 `rejected`，不得直接放大自动化规模。
3. CSIS 只保留 `/analysis` 主入口，RSS 旧活动页来源和重复 website 来源均不再参与试运行。
4. AEI 继续保留 `web_article_allowed` 特例，但要重点检查转载页、导流页、原始出处和正文长度。
5. Heritage、CAP、Cato 在找到稳定公开入口前保持 `blocked`，不进入自动入库试运行。
6. RAND 第二次受控试写、AI 生成与人工复核已完成，report 439 已通过；正式 `pilot_crawl` 试抓已通过策略守卫，本轮候选均因重复被跳过；后续仍保持每次最多新增 1 篇和人工复核。
7. Carnegie 已修复 `Full Text (PDF)` 识别并完成受控试写、AI 生成、人工复核通过和正式 `pilot_crawl` 试抓；Atlantic Council 已扩展 PDF 发现入口，完成 report 344、441、442 三篇复核通过样本，并增加无 PDF 候选发现阶段预检；后续仍保持每次最多新增 1 篇和人工复核。
8. 后续新增老师重点名单来源仍按 `docs/source-onboarding-playbook.md` 的“只读审计 -> 小样本复核 -> pilot_crawl”流程执行。
