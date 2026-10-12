# ECFR 准入建议

更新时间：2026-09-22

本文用于整理 `ecfr` 从 `standard_review` 进入下一阶段前的证据、风险和建议动作。详细过程见 [non-us-source-readonly-audit-20260921.md](non-us-source-readonly-audit-20260921.md)。

## 一、当前结论

ECFR 已完成准入验证，并已准备进入正式小批量试运行：

- ECFR 已经通过解析器、只读审计、人工试写、AI 生成、前端复核的闭环验证。
- ECFR 已有 2 篇 `success + approved` 样本，其中 1 篇 PDF、1 篇网页长文。
- ECFR 的候选发现质量较好，但报告形态同时包含 PDF 和长网页，需要单独明确文档准入口径。
- 曾发生过 `standard_review` 来源被后台常规 crawler 误批量入库的问题；虽然已加 rollout guard，但在升级前应再观察一轮。

当前状态：

| 项目 | 建议 |
| --- | --- |
| rollout stage | `pilot_crawl` |
| source active | 可保持 active |
| 常规自动入库 | 允许，但仍限制小批量 |
| 人工受控抓取 | 仍可用于验证，每次最多 1 篇 |
| 文档策略 | `web_article_allowed` |
| 升级时点 | 2026-09-22 已满足升级条件 |

## 二、已验证证据

### 1. 解析器可用

ECFR parser 当前覆盖以下入口：

- `https://ecfr.eu/topic/china/`
- `https://ecfr.eu/category/china/`
- `https://ecfr.eu/publications/`
- `https://ecfr.eu/`

候选范围限定为 `/publication/` 路径下的报告型内容，并排除 `Commentary`、`Podcast`、`Event`、普通 `/article/`。

### 2. 只读审计通过

只读审计结果：

| 字段 | 结果 |
| --- | ---: |
| raw_candidates | 18 |
| unique_candidates | 18 |
| checked_candidates | 3 |
| document_ok | 3 |
| document_failed | 0 |

抽查样本覆盖 PDF 和网页长文，说明 ECFR 候选发现和正文获取都具备基础可用性。

### 3. 两篇真实样本已通过闭环

| 报告 ID | 标题 | 文档形态 | 正文质量 | AI 结果 | 前端复核 |
| ---: | --- | --- | --- | --- | --- |
| 398 | The art of the swarm: Systemic rivalry with China on European terms | PDF，26 页 | 合格 | `success` | `approved` |
| 420 | The future is fermented: How Europe can succeed in the next industrial race | 网页长文，43,866 字符 | 合格 | `success` | `approved` |

这两篇样本说明：

- ECFR 的 PDF 报告可满足 20 页以上长报告要求。
- ECFR 的网页长文也可能具备正式报告价值。
- 当前 AI 分块链路能够处理 ECFR 长文并生成符合字数要求的翻译、主要观点和深层研判。

## 三、主要风险

### 1. 文档形态混合

ECFR 不只发布 PDF。部分 `/publication/` 页面没有 PDF，但正文长度和结构接近报告。若仍使用默认 `pdf_20_page_required`，会误伤有效网页长文；若直接放宽为 `web_article_allowed`，又要防止短评论、访谈、播客或活动页混入。

建议：

- ECFR 可接受 `web_article`，但只限 `/publication/` 路径和报告型标签。
- 继续排除 `Commentary`、`Podcast`、`Event`、普通 `/article/`。
- 网页长文应保留正文长度门槛，并在前端复核中重点检查是否为正式政策研究。

### 2. 误批量入库历史

ECFR 曾因 source active 且常规 crawler 缺少 rollout guard，被后台自动任务批量入库 17 篇。该问题已修复并通过测试，但它提醒我们：非美国来源升级时不能只看解析器成功，还要看调度和提醒噪声。

建议：

- 升级前继续保留每次最多 1 篇。
- 升级后也先维持单次新增 1 篇，不扩大抓取规模。
- 观察通知、重复率、跳过原因和 AI finalizer 失败率。

### 3. AI finalizer 字数边界

报告 420 的 finalizer 首次因深层研判 2,549 字符超出上限失败，自动重试后成功。这不是来源阻断问题，但说明长网页报告在总结和评论稿字数控制上有轻微波动。

建议：

- 当前不需要重写 AI 流程。
- 后续若同类失败重复出现，再优化 finalizer prompt 或字数校验策略。
- 复核时保留 `needs_rerun` 作为人工兜底。

## 四、准入建议

### 推荐方案

ECFR 已完成过渡验证，可进入正式小批量试运行。

执行方式：

1. ECFR source 保持 active。
2. rollout policy 升级为 `pilot_crawl`。
3. 仍可通过人工命令新增样本，保持单次最多 1 篇：

```bash
docker exec thinktank-backend python -m app.scripts.pilot_crawl_sources --keys ecfr --allow-standard-review --max-saved 1 --max-candidates 5 --ai-status skipped
```

4. 每新增 1 篇，按以下顺序复核：

- 先看正文质量。
- 正文合格后触发 AI。
- AI 成功后前端复核翻译、主要观点和深层研判。
- 合格后标记 `approved`。

5. 升级后继续观察 1-2 轮，若出现短评论混入、网页长文质量波动或通知噪声，应回退到受控试运行。

## 五、正式升级条件

ECFR 已满足以下条件，已可修改 `source_rollout_policy.py`：

| 条件 | 当前状态 | 是否满足 |
| --- | --- | --- |
| 至少 2 篇真实入库样本通过 AI 和前端复核 | 398、420 已通过 | 是 |
| 同时覆盖 PDF 和网页长文 | 398 为 PDF，420 为网页长文 | 是 |
| 常规 crawler guard 已修复并测试 | 23 项相关测试通过 | 是 |
| 无新增通知噪声 | 失败通知已清理，当前为 0 | 是 |
| 再观察 1-2 篇人工受控样本 | 第 3 篇样本 `421` 已完成 AI 和前端复核 | 是 |
| 明确 ECFR 文档策略 | `web_article_allowed` | 是 |

升级时已同步修改：

- `backend/app/services/source_rollout_policy.py`
- `backend/tests/test_source_rollout_policy.py`
- `docs/source-rollout-status.md`
- `docs/non-us-source-readonly-audit-20260921.md`

升级后的策略：

| 字段 | 建议值 |
| --- | --- |
| `rollout_stage` | `pilot_crawl` |
| `document_policy` | `web_article_allowed` |
| `can_run_pilot_crawl` | `True` |
| 单次保存 | 仍限制为最多 1 篇 |
| 复核要求 | AI 成功后必须人工复核 |

## 六、给老师的说明口径

ECFR 已经通过两个真实样本验证，能够稳定提供欧盟对华政策视角，且报告形态覆盖 PDF 和网页长文。当前建议不是立即完全自动放开，而是将 ECFR 作为欧洲来源的首个重点试运行对象，继续以“每次 1 篇、人工复核”的方式观察 1-2 轮。这样既能补足美国之外的重要政策视角，也能控制短评论混入、重复入库和通知噪声。

## 七、下一步建议

建议下一步选择其一：

| 选项 | 动作 | 适用情况 |
| --- | --- | --- |
| A | 继续第 3 篇 ECFR 受控样本 | 想再积累 1 篇证据后升级 |
| B | 直接准备升级代码，但仍保持每次最多 1 篇 | 认为 2 篇样本已足够，愿意进入正式小批量试运行 |
| C | 暂停 ECFR，转向 Bruegel/JIIA/KIEP 解析器 | 想扩大非美国来源横向覆盖 |

当前执行进展：

- 已选择选项 A，继续第 3 篇 ECFR 受控样本。
- `crawl_run_id=679` 新增报告 `421`：`Beijing hold’em: European cards against Chinese coercion`。
- 报告 `421` 为官方 PDF，24 页，有效文本页 17 页，正文 29,471 字符。
- 正文质量和 AI 成果均已前端确认合格，当前 `ai_status=success`、`review_status=approved`。

更新后的判断：

- ECFR 已有 3 篇 `success + approved` 样本。
- 样本覆盖 PDF 和网页长文。
- 当前通知噪声为 0。
- 常规 crawler rollout guard 已修复并经过测试。

当前状态：已将 `ecfr` 加入 `PILOT_CRAWL_KEYS`，并将其文档策略设为 `web_article_allowed`。升级后仍保持每次最多新增 1 篇、AI 成功后前端复核，不扩大单次抓取规模。
