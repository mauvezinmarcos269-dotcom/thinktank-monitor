# Brookings / RAND RSS 入口只读核验

核验日期：2026-10-02，Asia/Shanghai。

## 范围与方法

- 只读取来源健康接口、运行历史和公开官网内容，不触发正式采集、报告入库、AI 生成或来源更新。
- 复用项目已有 `fetch_resource`、`httpx`、`BeautifulSoup`、`feedparser` 和 `parse_rss_articles`，不安装新依赖。
- 以项目 HTTP 客户端的实际响应为主要依据，核对状态码、最终 URL、内容类型和条目数；另记录 Brookings 的 GET 跳转链。
- RSS 链接仅从官网 HTML 或官方文章提取，不拼接猜测替代地址；保留证书验证，不通过忽略 TLS 错误强行接入。
- 证据和修改前文档备份保存在 `.codex-backups/rss-readonly-audit-20261002-234017/`，临时核验脚本位于同一目录，不进入业务代码。

## 只读核验时的来源与失败历史

以下为停用前快照；用户确认后的停用执行结果见文末。

| 来源 | source_id | 当前 URL | active | 最近三次运行 | 入库报告数 |
| --- | --- | --- | --- | --- | --- |
| Brookings RSS | 52 | `https://www.brookings.edu/feed/` | true | 740、720、712，均 HTML 解析失败 | 0 |
| RAND RSS | 54 | `https://www.rand.org/rss.xml` | true | 746、731、653，均 HTTP 404 | 0 |
| Brookings website | 1 | `https://www.brookings.edu/` | true | 最新 743 成功 | 13 |
| RAND website | 7 | `https://www.rand.org/` | true | 最新 744 成功 | 11 |

两个机构的网站源与 RSS 源是不同记录。机构已经进入 `pilot_crawl`，不代表每个 RSS 入口都可用；本次只读核验不改变机构准入状态或 PDF 门槛。

## Brookings 核验结果

- 现有 `/feed/` 的 GET 响应为 `302 Location: /`，跟随跳转后到达首页，最终 `200 text/html; charset=UTF-8`。
- 正文以 `<!DOCTYPE html>` 开始，页面标题为 Brookings 首页标题；项目 RSS parser 按预期拒绝 HTML，而不是将首页当作空订阅成功处理。
- [官网首页](https://www.brookings.edu/)、[中国专题页](https://www.brookings.edu/regions/asia-the-pacific/china/)及[订阅页](https://www.brookings.edu/newsletters/)的 HTML 仍声明 `/feed/` 为 `application/rss+xml`，但实际请求不是 RSS。不能只凭页面声明认定入口有效。
- [官方 PlanetPolicy 旧文](https://www.brookings.edu/articles/new-planetpolicy-blog-focuses-on-climate-and-energy-solutions/)包含另一个 RSS 链接：`http://webfeeds.brookings-edu-2023.go-vip.net/brookingsrss/topfeeds/planetpolicy?format=xml`。
- 原始 HTTP 链接及其 HTTPS 地址在本环境均因证书主机名不匹配而无法完成请求。未关闭证书验证，未取到可审计条目；该链接还是气候/能源栏目，不是涉华报告入口，不能作为当前源的合格替代。
- 官网订阅页提供包括 China Bulletin 在内的邮件订阅，但邮件订阅表单不等于 RSS，也未在本步提交订阅。

结论：当前配置的 RSS 入口失效；在本次核验范围内，未找到已验证可用、内容适合涉华报告监测的替代 feed。无法据此断言 Brookings 全站不再提供任何 RSS。

## RAND 核验结果

- 现有 `/rss.xml` 实际返回 `404 text/html; charset=UTF-8`，页面标题为 `PAGE NOT AVAILABLE (Error 404) | RAND`；项目 HTTP 客户端在解析前按预期抛出状态异常。
- 官网首页、`/pubs.html`、`/pubs/research_reports.html` 和 `/newsletters.html` 均返回 200；这些页面中的 OpenSearch XML 不是研究报告 RSS，首页播客 XML 也不作为报告订阅入口。
- [官方中国专题页](https://www.rand.org/topics/china.html)的 HTML 明确声明 `https://www.rand.org/topics/china.xml` 为 RSS 链接，地址来源可追溯，不是猜测。
- [China feed](https://www.rand.org/topics/china.xml)两次请求均返回 `200 application/xml`，大小 514 字节，实际为 Atom，标题 `RAND Research Topic: China`。
- `feedparser` 判断 XML 无格式错误；标准 `ElementTree` 检查为 0 个 Atom entry、0 个 RSS item；项目 parser 两次均返回 0 条文章。正文确实没有条目，不是 parser 漏读。
- 中国专题网页同时展示多篇研究内容，因此本次空 Atom feed 不能作为报告覆盖已经恢复的证据，也无法进行条目类型、PDF 页数和入库质量抽样。

结论：找到官方发布的候选替代地址，但当前没有条目，暂不建议用它直接替换 active RSS。可在后续人工确认或只读复查出现真实条目后，再审计其内容和文档质量。

## 验证与建议

以下为只读核验阶段的验证和建议，后续授权执行情况见下一节。

- `poetry run pytest tests/test_rss_parser.py -q`：5 项测试通过。
- `sources-before.json` 与 `sources-after.json` 对四个来源的完整健康快照逐项比较一致，包括 URL、active、更新时间、报告数和最近运行；本步未改变配置或运行状态。
- 基于连续失败、当前实际响应和已有正常网站入口，建议用户确认后只停用失效 RSS `52`、`54`，保留网站源 `1`、`7`；不删除来源、不改 URL、不修改机构 rollout、不放宽 20 页 PDF 门槛。
- 停用建议只是减少失效入口的重复失败，并不证明网站源能够覆盖所有新报告，也不代表监测已达到实时；当前两个网站源配置的抓取间隔均为 1440 分钟，监测频率需另行确认。
- 若获准执行停用，先备份来源快照，再核对接口和页面仅这两条来源变为停用、历史记录仍可查看，且正常网站源仍保持 active。
- 邮件订阅作为可选人工补充渠道，接入邮件账户或自动读取邮件需要另行确认，未在本步实施。

主要证据文件：`official-http-checks.json`、`brookings-redirect-check.json`、`official-link-checks.json`、`research-entry-checks.json`、`rand-china-feed-check.json`、`rand-china-feed-xml-recheck.json`、`sources-before.json`、`sources-after.json`。

## 用户确认后的 RSS 停用执行

执行时间：2026-10-02 23:54:20，Asia/Shanghai。

- 用户已确认仅停用 RSS `52`、`54`，保留网站源 `1`、`7` 及全部历史记录。
- 修改前已备份 56 个来源配置、完整健康结果、两个 RSS 源的抓取历史和相关文档到 `.codex-backups/rss-disable-20261002-235214/`。
- 通过现有管理接口分别执行 `PATCH /api/v1/sources/52` 和 `PATCH /api/v1/sources/54`，请求体均仅为 `{"is_active": false}`，两次均返回 200。
- 前后配置逐字段比较，仅目标来源的 `is_active` 与自动更新时间 `updated_at` 变化；其余 54 个来源完全一致，全部来源的报告数量和最近运行记录未变。
- 两个 RSS 源分别保留 24 条、17 条历史运行，前后历史接口响应完全一致；URL、频率、历史错误及机构准入策略未修改，也未创建采集或 AI 任务。

| 指标 | 停用前 | 停用后 |
| --- | --- | --- |
| 来源总数 | 56 | 56 |
| active 来源 | 54 | 52 |
| 停用来源 | 2 | 4 |
| 失败来源 | 36 | 34 |
| 前端需处理来源 | 48 | 46 |

实际页面核验：

- 设置页仍显示全部 56 个来源，RSS `52`、`54` 均显示“停用”和“来源已停用”，手动重试按钮禁用。
- 两个来源最近三条失败历史仍展示，按 URL 搜索各得到 1 条；清除搜索后恢复 56 条。
- “需处理”按钮数量与实际列表均为 46，两个停用 RSS 不在列表中；正常网站源 `1`、`7` 继续启用，重试按钮可用。
- RAND 网站源原有无 PDF 候选处理提示仍保留，未因停用 RSS 而被错误隐藏。
- 浏览器控制台和网络未发现错误，页面走查只发出 GET 及正常的 CORS OPTIONS 预检；未提交新的配置更新或采集任务。
- 桌面截图、逐项核对结果和请求记录已保存为 `brookings-rss-disabled.png`、`rand-rss-disabled.png`、`page-checks.json`。

停用验收时发现展示问题：停用来源仍沿用“当前无需人工处理，继续观察自动抓取结果”和机构试运行建议。这不影响停用标志及重试禁用，但文案易误导；后续已按用户确认于 2026-10-03 修复，详见下一节。

本步仅更新来源启用标志及操作文档，未修改业务代码。配置备份可用于后续经用户确认的恢复操作，本步未执行恢复。

## 2026-10-03 停用来源提示统一

- 用户确认后，为来源列表增加独立的停用展示分支，使用灰色提示“此来源已停用，后续自动抓取已暂停。历史记录保留。”。
- 停用来源隐藏抓取诊断建议和试运行建议；准入标签明确为“机构准入”，保留该机构已通过样本复核的信息。
- 停用来源的频率、问题和最近错误分别标注为“原抓取频率”“停用前问题”“停用前最近错误”，原始错误和抓取历史仍可查看。
- 修改局限于 `source-health-list.tsx` 和相关 CSS；启停状态、筛选逻辑、历史接口及抓取流程未调整。
- 实际页面核对四个停用来源 `52`、`53`、`54`、`55`：均显示新提示，不显示自动抓取建议，重试按钮保持禁用；正常 Brookings 和 RAND 网站源的提示及按钮保持正常。
- 当前页面“需处理”按钮与实际列表均为 45 条，四个停用来源均不在其中；本次核验前后的来源健康接口快照完全一致，此数量不作为文案修改造成的变化。
- 已打开停用 CSIS website 来源 `55` 的历史运行 `570`，5 条候选仍可正常读取。
- 1440 x 1000 桌面及 390 x 844 窄屏截图检查通过，窄屏提示文字无溢出；浏览器未发现前端或接口错误。
- `npm run typecheck`、`npm run lint` 通过。修改前文件备份、接口快照、页面核对记录和截图保存在 `.codex-backups/disabled-source-copy-20261003-191556/`。
