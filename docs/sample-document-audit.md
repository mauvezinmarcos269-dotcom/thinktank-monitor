# 真实抓取闭环小样本复核

更新时间：2026-09-12

本文档记录只读小样本复核结果。复核脚本只执行候选发现、PDF/长文获取和
20 页门槛检查，不写数据库、不发通知、不调用 LLM。

运行命令：

```bash
poetry run python -m app.scripts.audit_source_documents \
  --keys aei,heritage,cfr \
  --max-candidates 3 \
  --discovery-timeout 90 \
  --document-timeout 120
```

## 结果概览

| 来源 | 原始候选 | 检查候选 | 通过文档门槛 | 失败候选 | 主要结论 |
| --- | ---: | ---: | ---: | ---: | --- |
| Heritage | 9 | 3 | 1 | 2 | 可产出合格 PDF，但部分报告页返回 403 |
| CFR | 1 | 1 | 1 | 0 | 候选少但质量高，样本 PDF 刚好 20 页 |
| AEI | 13 | 3 | 0 | 3 | 候选召回多，但 PDF/页数门槛过滤明显 |

## 样本明细

### Heritage

- 通过：`Winning the New Cold War: A Plan for Countering China`
  - PDF：`https://www.heritage.org/sites/default/files/2023-03/China_Plan.pdf`
  - 页数：143 页，非空页 141 页，正文约 421937 字符
- 失败：`Xi Comes to Washington: Expectations for the Trump-Xi Summit`
  - 原因：详情页返回 `403 Forbidden`
- 失败：`Armed by China: The Dependency Behind Pakistan's Military`
  - 原因：详情页返回 `403 Forbidden`

### CFR

- 通过：`Out of Ammo: A Two-Year Sprint to Rebuild the American Arsenal and Deter China`
  - PDF：`https://assets.cfr.org/images/Out-of-Ammo_9-3/Out-of-Ammo_9-3.pdf`
  - 页数：20 页，非空页 20 页，正文约 39593 字符

### AEI

- 失败：`Flipping the Script: How to Hold China's New Carriers at Risk`
  - 原因：详情页未发现 PDF 链接
- 失败：`Dataset: China Global Investment Tracker`
  - 原因：详情页未发现 PDF 链接
- 失败：`China's Outbound Investment Shrugs Off the Iran War`
  - 原因：PDF 页数不足，16 页，未达到 20 页门槛

## 后续处理建议

1. 优先把 CFR、Heritage 作为第一批入库抓取试点来源，因为已验证能产出合格 PDF。
2. Heritage 需要单独处理 403：判断是站点防护、请求头不足，还是这些报告页面已限制访问。
3. AEI 应继续保留在候选发现中，但真实入库前要接受较高跳过率；当前已确认网页长文可正式入库，可按长文 HTML 口径继续复核。

## 入库前质量策略

当前策略已固化为 `source_rollout_policy`，用于指导试运行抓取，不改变数据库结构。

| 来源 | 策略 | 文档口径 | 是否可进入第一批试运行 | 说明 |
| --- | --- | --- | --- | --- |
| CFR | `pilot_crawl` | `pdf_20_page_required` | 是 | 小样本已验证合格 PDF，可先小批量入库观察 |
| Heritage | `pilot_crawl` | `pdf_20_page_required` | 是 | 可产出高质量 PDF，但要继续记录 403 跳过样本 |
| AEI | `discovery_only` | `web_article_allowed` | 否 | 候选多但 PDF/页数门槛失败率高，已允许足够长、报告型网页正文作为正式报告入库 |
| Cato | `blocked` | `source_access_blocked` | 否 | 普通 HTTP 当前被站点防护拦截，需先解决入口可达性 |

默认策略：未完成真实小样本文档复核的来源为 `standard_review`，不得直接进入批量入库抓取。

## 小批量真实入库试运行

运行命令：

```bash
poetry run python -m app.scripts.pilot_crawl_sources \
  --keys cfr,heritage \
  --max-saved 1 \
  --max-candidates 3 \
  --ai-status skipped
```

运行设置：

- 每个来源最多保存 1 篇。
- 每个来源最多检查 3 个候选。
- 不加 `--notify`，因此不创建站内通知。
- AI 状态为 `skipped`，避免 Celery 自动排队；确认样本质量后可再手动重置 AI。

运行结果：

| 来源 | Crawl Run ID | 检查候选 | 新增入库 | 结果说明 |
| --- | ---: | ---: | ---: | --- |
| CFR | 268 | 3 | 0 | 前 3 个候选均已存在，未新增 |
| Heritage | 269 | 3 | 1 | 成功新增 1 篇，未触发通知，AI 暂不排队 |
