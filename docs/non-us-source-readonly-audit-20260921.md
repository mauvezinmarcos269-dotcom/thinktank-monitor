# 非美国/周边来源只读审计记录

更新时间：2026-09-22

本轮目标是在不入库、不通知、不触发 AI 的前提下，验证非美国重点来源是否已具备候选发现和文档质量审计基础。

## 审计命令

```bash
docker exec thinktank-backend python -m app.scripts.audit_source_documents --keys chatham_house,ecfr,bruegel,jiia,kiep --max-candidates 3 --discovery-timeout 90 --document-timeout 120
```

## 候选选择

本轮选择 5 个来源，覆盖欧洲和周边国家：

| key | 来源 | 层级 | 区域 | 选择理由 |
| --- | --- | --- | --- | --- |
| `chatham_house` | Chatham House | P2 | europe | 英国代表性国际事务智库 |
| `ecfr` | European Council on Foreign Relations | P2 | europe | 欧盟对外政策和对华政策重点来源 |
| `bruegel` | Bruegel | P2 | europe | 欧洲经贸、产业和全球经济治理重点来源 |
| `jiia` | Japan Institute of International Affairs | P3 | neighboring | 日本外交安全政策重点来源 |
| `kiep` | Korea Institute for International Economic Policy | P3 | neighboring | 韩国对外经济和区域经济政策重点来源 |

## 审计结果

| key | 状态 | 结果 | 说明 |
| --- | --- | --- | --- |
| `bruegel` | `discovery_error` | 未进入文档检查 | 尚未配置 `https://www.bruegel.org/` 的专用 website 解析器 |
| `chatham_house` | `discovery_error` | 未进入文档检查 | 尚未配置 `https://www.chathamhouse.org/` 的专用 website 解析器 |
| `ecfr` | `discovery_error` | 未进入文档检查 | 尚未配置 `https://ecfr.eu/` 的专用 website 解析器 |
| `jiia` | `discovery_error` | 未进入文档检查 | 尚未配置 `https://www.jiia.or.jp/` 的专用 website 解析器 |
| `kiep` | `discovery_error` | 未进入文档检查 | 尚未配置 `https://www.kiep.go.kr/` 的专用 website 解析器 |

## 结论

- 本轮没有新增入库、没有发通知、没有触发 AI。
- 5 个非美国/周边候选来源均停留在候选发现前置阶段，主要阻塞点不是文档质量，而是缺少专用解析器。
- 暂不应将上述来源加入 `pilot_crawl`。
- 下一步应先为 1 个来源实现最小可用解析器，再重新执行只读审计。

## 下一步建议

优先从 `chatham_house` 或 `ecfr` 中选择一个来源做解析器试点：

- `chatham_house`：适合作为英国/英联邦政策圈代表来源，研究报告形态相对稳定。
- `ecfr`：适合作为欧盟对华政策代表来源，政策评论和专题内容多，需要严格区分长报告与短评论。

建议先只实现候选发现，不直接入库；待只读审计能返回 3 条以上候选，再检查 PDF/网页正文质量和涉华相关性。

## 2026-09-21 Chatham House 最小解析器验证

本轮已为 `chatham_house` 增加最小可用 website 解析器：

- 入口：`https://www.chathamhouse.org/`
- 解析范围：首页 `<article>` 内容卡片。
- 候选类型：仅保留 `Research paper`、`Research report`、`Policy paper`、`Policy brief`、`Briefing`、`Report`、`Paper` 等报告型标签。
- 过滤规则：非 China 专题页必须在标题、URL 或卡片摘要中出现涉华信号。
- 排除规则：`Expert comment` 等短评论不作为正式报告候选。

验证命令：

```bash
docker exec thinktank-backend python -m app.scripts.audit_source_documents --keys chatham_house --max-candidates 3 --discovery-timeout 90 --document-timeout 120
```

验证结果：

| 字段 | 结果 |
| --- | --- |
| status | `ok` |
| rollout_stage | `standard_review` |
| raw_candidates | 0 |
| unique_candidates | 0 |
| checked_candidates | 0 |
| document_ok | 0 |
| document_failed | 0 |

结论：

- Chatham House 已从“未配置解析器导致 discovery_error”推进为“解析器可运行”。
- 当前首页没有符合“报告型标签 + 涉华信号”的候选，因此未进入文档质量检查。
- Chatham House 仍不应进入 `pilot_crawl`。
- 下一步可以继续寻找更稳定的 Chatham House 报告列表、搜索页、专题页、站点地图或 RSS/API；若入口仍受 403 限制，可转向 `ecfr` 做第二个非美国解析器试点。

## 2026-09-21 ECFR 最小解析器验证

本轮已为 `ecfr` 增加最小可用 website 解析器：

- 入口：`https://ecfr.eu/topic/china/`、`https://ecfr.eu/category/china/`、`https://ecfr.eu/publications/`、`https://ecfr.eu/`。
- 解析范围：`/publication/` 路径下的报告型内容卡片。
- 候选类型：`Policy Brief`、`Policy Alert`、`Special`、`Book`、`Report`。
- 排除规则：`Commentary`、`Podcast`、`Event`、普通 `/article/` 不作为正式报告候选。
- 非 China 专题页必须在标题、URL 或卡片摘要中出现涉华信号。

验证命令：

```bash
docker exec thinktank-backend python -m app.scripts.audit_source_documents --keys ecfr --max-candidates 3 --discovery-timeout 90 --document-timeout 120
```

验证结果：

| 字段 | 结果 |
| --- | --- |
| status | `ok` |
| rollout_stage | `standard_review` |
| raw_candidates | 18 |
| unique_candidates | 18 |
| checked_candidates | 3 |
| document_ok | 3 |
| document_failed | 0 |

样本结果：

| 标题 | 文档形态 | 页数/长度 | 结论 |
| --- | --- | --- | --- |
| The art of the swarm: Systemic rivalry with China on European terms | `pdf` | 26 页，57,736 字符 | 通过 |
| The future is fermented: How Europe can succeed in the next industrial race | `web_article` | 43,866 字符 | 通过 |
| Beijing hold’em: European cards against Chinese coercion | `pdf` | 24 页，29,471 字符 | 通过 |

结论：

- ECFR 已具备候选发现和文档质量审计基础。
- 本轮只读审计中 3/3 样本文档通过，质量明显优于第一轮未配置解析器状态。
- ECFR 当前仍保持 `standard_review`，不直接入库。
- 下一步可对 ECFR 执行“人工试写 1 篇、AI 状态 skipped”的小批量验证；通过前不应升级为 `pilot_crawl`。

## 2026-09-22 ECFR 人工试写异常与清理

原计划是在 ECFR 仍处于 `standard_review` 的前提下，人工写入 1 篇样本，并保持 `ai_status=skipped`，用于前端复核报告正文质量。

实际执行时发现一个准入保护问题：

- 人工命令 `crawl_run_id=647` 返回 `saved_count=0`，跳过原因为 `concurrent_duplicate`。
- 进一步排查发现后台常规 crawler 已提前执行 `crawl_run_id=646`，对 ECFR 批量保存 17 篇报告。
- 根因是常规 crawler 只检查来源是否 active，没有再次校验来源 rollout policy；ECFR 虽然仍是 `standard_review`，但 source 处于 active 状态，因此被后台自动任务误抓取。

清理处理：

| 项目 | 处理结果 |
| --- | --- |
| ECFR source `source_id=21` | 已临时设为 `is_active=False`，防止后台继续自动抓取 |
| 保留样本 | 仅保留报告 `398`，标题为 `The art of the swarm: Systemic rivalry with China on European terms` |
| 删除样本 | 删除误入库报告 `399`、`401-415`，共 16 篇 |
| AI 状态 | 报告 `398` 已重置为 `ai_status=skipped`，清空误触发 AI 产物和分块 |
| 复核状态 | 报告 `398` 保持 `pending_review`，作为 ECFR 人工试写保留样本 |
| 通知噪声 | 已删除本次误入库产生的 ECFR 相关通知 21 条 |
| 备份 | 清理前数据已备份至 `docs/backups/20260922-ecfr-cleanup-before-policy-fix/` |

代码修复：

- 已在常规 crawler 入口增加 rollout policy guard。
- 只有 `get_source_rollout_policy(key).can_run_pilot_crawl=True` 的来源才能进入自动入库抓取。
- `standard_review`、`discovery_only`、`blocked` 等阶段即使 source active，也会被拒绝自动入库。
- 已增加单元测试覆盖 ECFR 被拦截、Brookings 可放行两种场景。

验证结果：

| 验证项 | 结果 |
| --- | --- |
| `pytest tests/test_crawler_service.py tests/test_ecfr_parser.py tests/test_chatham_house_parser.py` | 23 passed |
| `ruff check ...` | All checks passed |
| ECFR 当前报告数 | 仅剩 `398` |
| ECFR 当前通知数 | 0 |
| ECFR 当前来源状态 | `is_active=False` |

下一步：

- 请先在前端复核报告 `398` 的正文质量：`http://localhost:3000/reports?report_id=398&view=summary&focus=review`。
- 若 398 正文质量合格，再决定是否触发 AI 生成全文翻译和分析评论。
- ECFR 在你确认前仍保持 `standard_review` 和临时停用状态，不升级为 `pilot_crawl`。

## 2026-09-22 ECFR 398 AI 生成验证

经前端复核前检查，报告 `398` 正文质量合格：

- 官方 ECFR PDF，26 页，26 页均有有效文本。
- 正文长度 57,736 字符。
- 原文链接和 PDF 链接完整。

已按现有 `/retry-ai` 分块流程触发 AI 生成，任务 `f59dd21a-0a7f-431c-8f3a-9b4b5272065e` 已完成：

| 字段 | 结果 |
| --- | ---: |
| AI 状态 | `success` |
| 分块数量 | 24 |
| 分块结果 | 24/24 success |
| 全文翻译长度 | 17,704 字 |
| 主要观点长度 | 1,761 字 |
| 深层研判长度 | 2,113 字 |

触发 AI 前备份已保存至 `docs/backups/20260922-ecfr-398-before-ai/`。

前端人工复核结果：

- 报告 `398` 正文、全文翻译、主要观点和深层研判质量合格。
- 已标记为 `approved`。
- 复核意见：`ECFR 398 前端复核合格：正文、全文翻译、主要观点和深层研判质量通过；作为 ECFR 人工试写 approved 样本保留。`

ECFR 当前仍保持 `standard_review`，`source_id=21` 仍临时停用。下一步应由人工确认是否恢复 source 并继续执行“每次最多 1 篇”的小批量试写，而不是直接升级为常规 `pilot_crawl`。

## 2026-09-22 ECFR 第二篇受控样本

经人工确认后，已恢复 ECFR `source_id=21`：

- `is_active=True`
- `last_error=None`
- rollout policy 仍保持 `standard_review`
- 常规 crawler 已有 rollout policy guard，因此不会因 source active 而绕过准入阶段自动批量入库

随后执行受控抓取：

```bash
docker exec thinktank-backend python -m app.scripts.pilot_crawl_sources --keys ecfr --allow-standard-review --max-saved 1 --max-candidates 5 --ai-status skipped
```

运行结果：

| 字段 | 结果 |
| --- | --- |
| crawl_run_id | `678` |
| found_count | 5 |
| saved_count | 1 |
| 跳过原因 | 已入库重复 1 条，即报告 `398` |

新增样本：

| 报告 ID | 标题 | 文档形态 | 正文长度 | AI 状态 | 复核状态 |
| ---: | --- | --- | ---: | --- | --- |
| 420 | The future is fermented: How Europe can succeed in the next industrial race | `web_article` | 43,866 字符 | `skipped` | `pending_review` |

注意：

- 报告 `420` 是 ECFR 网页长文，不是 PDF。
- 该样本在只读审计阶段曾作为 ECFR 第二个质量样本通过正文长度检查。
- 是否将 ECFR 的长网页报告纳入可接受范围，需要前端人工复核后再决定。
- 触发 AI 前，应先确认报告 `420` 的正文形态和内容质量是否合格。

前端正文复核结果：

- 报告 `420` 网页长文正文质量合格。
- 已触发 AI 分块生成，任务 `48731e18-f629-423c-856a-58581c53a452`。
- 分块数量 19 个，其中翻译分块 16 个、分析分块 3 个，全部成功。
- finalizer 首次因深层研判长度 2,549 字符、超过 2,500 字符上限而失败；Celery 自动重试后成功。
- 自动重试成功后，已清理残留的误导性 `report.ai_failed` 通知。

AI 生成结果：

| 字段 | 结果 |
| --- | ---: |
| AI 状态 | `success` |
| 全文翻译长度 | 14,363 字 |
| 主要观点长度 | 1,973 字 |
| 深层研判长度 | 2,405 字 |

前端人工复核结果：

- 报告 `420` 网页长文正文、全文翻译、主要观点和深层研判质量合格。
- 已标记为 `approved`。
- 复核意见：`ECFR 420 前端复核合格：网页长文正文、全文翻译、主要观点和深层研判质量通过；作为 ECFR 第二篇 approved 样本保留。`

截至本节点，ECFR 已有 2 篇通过样本：

| 报告 ID | 文档形态 | AI 状态 | 复核状态 | 说明 |
| ---: | --- | --- | --- | --- |
| 398 | `pdf` | `success` | `approved` | 官方 PDF，26 页 |
| 420 | `web_article` | `success` | `approved` | 网页长文，43,866 字符 |

ECFR `source_id=21` 当前保持 active，但 rollout policy 仍为 `standard_review`，`can_run_pilot_crawl=False`。常规 crawler 不会自动批量入库；后续新增仍应使用人工受控命令，每次最多 1 篇。

## 2026-09-22 ECFR 第三篇受控样本

按照准入建议，继续执行第 3 篇人工受控样本：

```bash
docker exec thinktank-backend python -m app.scripts.pilot_crawl_sources --keys ecfr --allow-standard-review --max-saved 1 --max-candidates 5 --ai-status skipped
```

运行结果：

| 字段 | 结果 |
| --- | --- |
| crawl_run_id | `679` |
| found_count | 5 |
| saved_count | 1 |
| 跳过原因 | 已入库重复 2 条，即报告 `398` 和 `420` |

新增样本：

| 报告 ID | 标题 | 文档形态 | 页数/有效文本页 | 正文长度 | AI 状态 | 复核状态 |
| ---: | --- | --- | ---: | ---: | --- | --- |
| 421 | Beijing hold’em: European cards against Chinese coercion | `pdf` | 24 / 17 | 29,471 字符 | `skipped` | `pending_review` |

注意：

- 报告 `421` 是 ECFR 官方 PDF。
- 页数满足 20 页门槛，有效文本页 17 页，正文长度 29,471 字符。
- 前端正文复核质量合格，已触发 AI。

AI 生成过程：

- 任务 ID：`3dc42486-40c7-4415-9706-231e0c0f9666`
- 分块数量 12 个，其中翻译分块 10 个、分析分块 2 个，全部成功。
- finalizer 首次因深层研判长度 1,968 字符、低于 2,000 字符下限而失败。
- Celery 自动重试后成功，深层研判长度为 2,104 字。
- 自动重试成功后，已清理残留的误导性 `report.ai_failed` 通知。

AI 生成结果：

| 字段 | 结果 |
| --- | ---: |
| AI 状态 | `success` |
| 全文翻译长度 | 9,462 字 |
| 主要观点长度 | 1,675 字 |
| 深层研判长度 | 2,104 字 |

前端人工复核结果：

- 报告 `421` PDF 正文、全文翻译、主要观点和深层研判质量合格。
- 已标记为 `approved`。
- 复核意见：`ECFR 421 前端复核合格：PDF 正文、全文翻译、主要观点和深层研判质量通过；作为 ECFR 第三篇 approved 样本保留。`

截至本节点，ECFR 已有 3 篇通过样本：

| 报告 ID | 文档形态 | AI 状态 | 复核状态 | 说明 |
| ---: | --- | --- | --- | --- |
| 398 | `pdf` | `success` | `approved` | 官方 PDF，26 页 |
| 420 | `web_article` | `success` | `approved` | 网页长文，43,866 字符 |
| 421 | `pdf` | `success` | `approved` | 官方 PDF，24 页 |

ECFR 已满足“至少 2 篇真实样本通过 AI 和前端复核、覆盖 PDF 和网页长文、通知噪声清零、rollout guard 已修复”的升级前置条件。下一步可以准备将 ECFR 升级为 `pilot_crawl + web_article_allowed`，但升级后仍应保持每次最多新增 1 篇和前端人工复核。

## 2026-09-22 ECFR 升级后第一次正式试抓

ECFR 已升级为 `pilot_crawl + web_article_allowed` 后，执行第一次正式小批量试抓。本次不再使用 `--allow-standard-review`，用于验证升级后的 policy 能正常放行：

```bash
docker exec thinktank-backend python -m app.scripts.pilot_crawl_sources --keys ecfr --max-saved 1 --max-candidates 5 --ai-status skipped
```

运行结果：

| 字段 | 结果 |
| --- | --- |
| crawl_run_id | `680` |
| found_count | 5 |
| saved_count | 1 |
| policy 状态 | `pilot_crawl + web_article_allowed` |
| 跳过原因 | 已入库重复 3 条，即报告 `398`、`420`、`421` |

新增样本：

| 报告 ID | 标题 | 文档形态 | 页数/有效文本页 | 正文长度 | AI 状态 | 复核状态 |
| ---: | --- | --- | ---: | ---: | --- | --- |
| 422 | EV endgame: Stalling China’s export surge in Europe’s southern neighbourhood | `pdf` | 21 / 21 | 47,843 字符 | `skipped` | `pending_review` |

注意：

- 报告 `422` 是 ECFR 官方 PDF。
- 页数满足 20 页门槛，有效文本页 21 页，正文长度 47,843 字符。
- 当前尚未触发 AI，需先前端复核正文质量。
