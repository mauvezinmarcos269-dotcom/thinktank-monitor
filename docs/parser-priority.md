# 来源解析器扩展优先级清单

更新时间：2026-09-09

## 目标

本清单用于指导下一阶段的爬虫来源解析器扩展，优先解决当前平台无法稳定获取“重磅涉华研究报告”的来源。清单基于后端现有来源健康状态、最近抓取失败原因、候选报告统计以及当前已实现解析器能力整理。

当前后端网站解析器只覆盖 CSIS 网站来源；RSS 来源已有通用解析逻辑，但个别站点存在 feed 格式或地址问题。

## 排序原则

1. 先修投入小、收益高的问题，例如 RSS 解析容错和失效 RSS 地址。
2. 优先美国顶级智库，尤其是涉华、外交、安全、经济政策报告产出稳定的机构。
3. 已有 RSS 能稳定产出的站点，网站解析器优先级后移。
4. 对非美国来源，优先英欧日德韩等对华政策影响较大的机构。
5. 暂不把国内机构作为第一批解析器目标，除非老师明确要求覆盖国内智库动态。

## P0：先修复的非网站解析问题

### 1. Brookings RSS

- 来源 ID：52
- URL：`https://www.brookings.edu/feed/`
- 当前问题：RSS 解析失败，错误为 `undefined entity`。
- 建议动作：增强 RSS 解析容错，对 HTML/XML 实体异常做清洗或降级处理。
- 原因：Brookings 属于最高优先级来源，RSS 如果修好，可能比网站解析器更快产生稳定结果。

### 2. RAND RSS

- 来源 ID：54
- URL：`https://www.rand.org/rss.xml`
- 当前问题：返回 404。
- 建议动作：核验 RAND 当前可用 RSS 或改用网站解析器。
- 原因：RAND 报告篇幅、政策影响力和涉华安全议题相关性都很高。

## P1：第一批网站解析器

### 1. Brookings

- 来源 ID：1
- URL：`https://www.brookings.edu/`
- 当前问题：缺少 website 专用解析器。
- 优先原因：美国顶级智库，涉华、全球治理、科技、经济、国际关系报告价值高；RSS 当前也有格式问题。
- 建议范围：优先识别 report、research、article/report 类型页面，筛选 PDF 或长文报告。

### 2. RAND

- 来源 ID：7
- URL：`https://www.rand.org/`
- 当前问题：缺少 website 专用解析器，RSS 地址无效。
- 优先原因：高质量长报告密集，安全、防务、科技、亚太、中国议题匹配度高。
- 建议范围：优先解析 research reports、publications、PDF 下载页。

### 3. Carnegie Endowment

- 来源 ID：8
- URL：`https://carnegieendowment.org/`
- 当前问题：缺少 website 专用解析器。
- 优先原因：外交政策、地缘政治、中国与周边议题较强，适合作为涉华趋势监测来源。

### 4. Council on Foreign Relations

- 来源 ID：3
- URL：`https://www.cfr.org/`
- 当前问题：缺少 website 专用解析器。
- 优先原因：对美国外交政策话语影响大，涉华议题频繁。
- 注意事项：CFR 页面类型较多，需避免把短评论、新闻问答全部当作长报告。

### 5. Peterson Institute for International Economics

- 来源 ID：11
- URL：`https://www.piie.com/`
- 当前问题：缺少 website 专用解析器。
- 优先原因：中美经贸、产业政策、金融与全球经济治理相关性强。

## P2：第二批美国网站解析器

### 1. Heritage Foundation

- 来源 ID：2
- URL：`https://www.heritage.org/`
- 优先原因：对美国保守派政策圈影响较大，涉华政策立场鲜明。
- 注意事项：需要区分报告、背景简报、评论文章。

### 2. American Enterprise Institute

- 来源 ID：6
- URL：`https://www.aei.org/`
- 优先原因：美国政策圈影响较大，外交、安全、经济议题均有产出。

### 3. Hoover Institution

- 来源 ID：10
- URL：`https://www.hoover.org/`
- 优先原因：涉华意识形态、安全与科技议题较多。

### 4. Wilson Center

- 来源 ID：12
- URL：`https://www.wilsoncenter.org/`
- 优先原因：国际与区域问题资料丰富，但需过滤活动、短新闻。

### 5. Cato Institute

- 来源 ID：4
- URL：`https://www.cato.org/`
- 优先原因：美国政策讨论中有一定影响力，经济与外交政策议题可补充。

### 6. Center for American Progress

- 来源 ID：13
- URL：`https://www.americanprogress.org/`
- 优先原因：偏民主党政策网络，适合平衡美国两党政策视角。

### 7. NBER

- 来源 ID：14
- URL：`https://www.nber.org/`
- 优先原因：经济研究质量高。
- 注意事项：严格说更接近学术工作论文来源，不是典型智库报告；可后置。

## P3：英欧及国际安全类来源

### 1. Chatham House

- 来源 ID：16
- URL：`https://www.chathamhouse.org/`
- 优先原因：英国核心外交政策智库，涉华与全球治理议题重要。

### 2. IISS

- 来源 ID：22
- URL：`https://www.iiss.org/`
- 优先原因：安全、防务、地缘政治报告价值高。

### 3. ECFR

- 来源 ID：21
- URL：`https://ecfr.eu/`
- 优先原因：欧洲对华政策、俄乌、印太议题相关。

### 4. Bruegel

- 来源 ID：15
- URL：`https://www.bruegel.org/`
- 优先原因：欧洲经济、贸易、产业政策相关。

### 5. SIPRI

- 来源 ID：23
- URL：`https://www.sipri.org/`
- 优先原因：安全与军控数据、报告质量较高。

### 6. IFRI / SWP / DGAP

- 来源 ID：18、19、20
- URL：`https://www.ifri.org/`、`https://www.swp-berlin.org/`、`https://dgap.org/`
- 优先原因：法德政策研究视角，对欧洲涉华认知有补充价值。

## P4：周边国家和区域经济来源

### 1. JIIA

- 来源 ID：24
- URL：`https://www.jiia.or.jp/`
- 优先原因：日本外交安全视角，对中国周边议题重要。

### 2. RIETI

- 来源 ID：25
- URL：`https://www.rieti.go.jp/`
- 优先原因：日本经济产业政策研究，可补充供应链、产业政策议题。

### 3. KIEP

- 来源 ID：28
- URL：`https://www.kiep.go.kr/`
- 优先原因：韩国对外经济政策研究，区域经济与对华经贸相关。

### 4. KDI / ERIA

- 来源 ID：27、26
- URL：`https://www.kdi.re.kr/`、`https://www.eria.org/`
- 优先原因：可作为区域经济和东盟相关补充来源。

## 暂缓项

### Atlantic Council 网站解析器

- 来源 ID：9
- URL：`https://www.atlanticcouncil.org/`
- 暂缓原因：RSS 来源 ID 51 已经能稳定抓取，并已有较多候选结果。
- 后续动作：等核心缺失来源补齐后，再做网站解析器作为召回增强。

### CSIS 网站解析器增强

- 来源 ID：5、55
- URL：`https://www.csis.org/analysis`、`https://www.csis.org/`
- 暂缓原因：RSS 来源 ID 53 已经可用；网站来源当前主要问题更像网络连接或页面结构差异。
- 后续动作：若老师要求更全覆盖 CSIS，再单独增强 CSIS 网站解析。

## 建议下一步

建议第 44 步优先做 Brookings RSS 容错修复。该项改动最小，成功后可立即恢复一个核心美国来源。

如果第 44 步后仍无法得到足够 Brookings 报告，再进入 Brookings 网站解析器开发。

建议后续站点开发顺序：

1. Brookings RSS 容错
2. Brookings website 解析器
3. RAND RSS 核验或 RAND website 解析器
4. Carnegie website 解析器
5. CFR website 解析器
6. PIIE website 解析器
7. Heritage / AEI / Hoover website 解析器
8. Chatham House / IISS / ECFR / Bruegel website 解析器

