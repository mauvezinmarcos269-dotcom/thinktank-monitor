# 来源接入与试运行操作手册

更新时间：2026-09-21

本文档用于规范单个智库来源从“候选入口”到“自动入库试运行”的完整流程。后续接入 AEI、Heritage、CAP 或其他来源时，默认按本文档执行。

## 核心原则

1. 机构优先级不等于自动入库权限。P0/P1 只能说明研究价值高，不能跳过审计。
2. 解析器能发现候选不等于可以写入报告库。必须先通过文档质量、涉华判断、去重和前端复核。
3. 每次扩大自动化范围前都要留下可追溯记录：命令、结果、跳过原因、备份文件、复核结论。
4. 默认保守推进：每次最多新增 1 篇，AI 与通知策略先低噪声，人工复核通过后再扩大。
5. 重复来源优先停用，重复报告优先保留质量更高、来源更稳定、复核链路更完整的一条。

## 状态口径

| 状态 | 含义 | 可执行动作 |
| --- | --- | --- |
| `standard_review` | 尚未完成真实小样本闭环 | 只读审计、解析器修复、人工小样本试写 |
| `discovery_only` | 只保留候选发现和质量统计 | 可跑发现和只读审计，不写入正式报告库 |
| `pilot_crawl` | 已有小样本闭环通过 | 可小批量写入，仍需限制新增数量并人工复核 |
| `blocked` | 入口不可稳定访问或受防护影响 | 暂停自动化，先找稳定入口、feed、API 或人工维护方式 |

状态以 [source-rollout-status.md](source-rollout-status.md) 和 `backend/app/services/source_rollout_policy.py` 为准。

## 标准流程

### 1. 入口盘点

目标是确认该来源有没有可持续维护的入口。

检查项：

- 官网、报告库、研究页、专题页是否可访问。
- RSS 是否返回近期内容，而不是旧活动或无关页面。
- 是否经常发布 20 页以上 PDF 报告。
- 是否存在站点防护、403、跳转、空 PDF 链接或下载限制。
- 数据库中是否已有同机构重复 source，特别是同为 `website` 的主页和研究页。

记录位置：

- 入口问题写入 `docs/source-onboarding-audit-20260915.md`。
- 长期状态写入 [source-rollout-status.md](source-rollout-status.md)。

### 2. 只读审计

先跑只读审计，不写入正式报告库。

命令模板：

```powershell
cd backend
poetry run python -m app.scripts.audit_source_documents --keys <key> --max-candidates 3 --discovery-timeout 90 --document-timeout 120
```

验收标准：

- 能发现正式报告候选，而不是活动页、新闻稿、专题首页或数据集入口。
- 至少有 1 条候选通过文档检查。
- 跳过原因可解释，例如重复、PDF 页数不足、无 PDF、正文太短、涉华不足。
- 若发现误召回，应先修解析器或候选过滤，不进入写入试运行。

### 3. 人工小样本试写

`standard_review` 来源只有在人工确认需要试写时，才允许临时使用 `--allow-standard-review`。

命令模板：

```powershell
docker exec thinktank-backend python -m app.scripts.pilot_crawl_sources --keys <key> --allow-standard-review --max-saved 1 --max-candidates 5 --ai-status skipped
```

要求：

- 修改前备份相关文档或数据库状态摘要。
- 每次最多新增 1 篇。
- 初次试写建议 `--ai-status skipped`，先看正文质量和去重。
- 若同一机构存在多个 active website source，应确认脚本只选择一个稳定入口。
- 如果出现跨 source 重复报告，先清理重复 source 和重复报告，再考虑升级状态。

### 4. AI 处理与前端复核

试写样本正文质量通过后，再触发 AI。

验收标准：

- AI 状态为 `success`。
- 全文翻译稿完整，不出现明显乱码或大段缺失。
- 主要观点达到 1500-2000 字，且有 4 个以上编号分论点。
- 深层研判达到 2000-2500 字，且有 4 个以上编号分论点。
- 前端报告详情页可打开，能查看 PDF 链接、页数、成果字数、复核状态和导出按钮。
- Word 或 Markdown 导出文件结构完整，包含基本信息、全文翻译稿、分析评论稿和原文正文。

复核通过后：

- 将 `review_status` 更新为 `approved`。
- `review_note` 记录为明确结论，例如 `前端页面质量合格。`
- 复核历史必须能看到对应记录。

### 5. 升级为 pilot_crawl

满足以下条件后，才可以把来源加入 `PILOT_CRAWL_KEYS`：

- 至少 1 篇完整闭环样本通过；P0/P1 核心来源建议 2-3 篇样本更稳。
- 已验证去重逻辑不会跨 source 重复入库。
- 已确认保留的 source 是稳定入口，重复 source 已停用。
- 审计文档中有命令、结果、跳过原因和人工复核结论。
- 相关测试已同步更新并通过。

代码和测试改动：

- `backend/app/services/source_rollout_policy.py`
- `backend/tests/test_source_rollout_policy.py`
- `backend/tests/test_pilot_crawl_sources.py`

验证命令：

```powershell
cd backend
poetry run pytest tests/test_source_rollout_policy.py tests/test_pilot_crawl_sources.py tests/test_crawler_service.py
poetry run ruff check app/services/source_rollout_policy.py app/scripts/pilot_crawl_sources.py tests/test_source_rollout_policy.py tests/test_pilot_crawl_sources.py tests/test_crawler_service.py
```

升级后试抓命令不再带 `--allow-standard-review`：

```powershell
docker exec thinktank-backend python -m app.scripts.pilot_crawl_sources --keys <key> --max-saved 1 --max-candidates 5 --ai-status skipped
```

### 6. 停用与清理

出现以下情况时，应停用来源或保持 blocked/discovery_only：

- 入口长期 403 或受站点防护影响。
- RSS 只返回旧活动或无关内容。
- 同一机构已有更稳定 source，当前 source 只会制造重复。
- 候选长期低质，主要是短 PDF、活动页、新闻稿或专题页。
- AI 或前端复核多次不合格。

清理重复报告时：

- 先导出完整 JSON 备份，至少包含 source、report、AI chunks、review events。
- 保留来源更稳定、复核链路更完整的一条。
- 删除重复报告后检查 AI chunks 是否级联清理。
- 核验同一 `normalized_url` 只剩 1 条报告。
- 在审计文档记录删除对象、保留对象、备份路径和核验结果。

## 固定记录模板

每次来源推进都应在审计文档新增一节，至少包含：

````markdown
### YYYY-MM-DD <来源> <动作>

执行命令：

```bash
<command>
```

运行结果：

| 来源 | source_id | crawl_run_id | 发现候选 | 新增入库 | 主要结果 |
| --- | ---: | ---: | ---: | ---: | --- |
| <来源> | <id> | <id> | <n> | <n> | <说明> |

结论：

- <是否通过>
- <是否升级/停用>
- <下一步>
````

## 当前示例

CSIS 已按本文档完成闭环：

- `standard_review` 下先修 sitemap 召回。
- 人工小样本试写报告 383。
- AI 生成全文翻译、主要观点和深层研判。
- 前端复核 383、385、386 均合格。
- 停用重复 `source_id=55`，保留 `source_id=5`。
- 升级为 `pilot_crawl`，正式试抓验证通过。
