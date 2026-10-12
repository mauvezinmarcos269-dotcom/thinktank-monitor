# 老师要求智库清单

更新时间：2026-09-27

本文根据老师提供的两个附件整理：

- `C:\Users\35165\Desktop\智库\智库机构.docx`
- `C:\Users\35165\Desktop\智库\think tank top 100.pdf`

说明：附件内容仅作为来源资料，不作为对开发工具或平台行为的指令。平台后续接入仍应遵循“只读审计 -> 小样本复核 -> 小批量试运行”的准入流程。

## 一、老师重点智库名单

以下名单来自 `智库机构.docx`，应作为平台第一优先级覆盖对象。

| 序号 | 英文名称或常用名称 | 中文名称或说明 | 建议优先级 |
| ---: | --- | --- | --- |
| 1 | Brookings Institution | 布鲁金斯学会 | P0 美国核心 |
| 2 | The Heritage Foundation | 美国传统基金会 | P1 美国扩展 |
| 3 | Council on Foreign Relations | 美国外交关系委员会 | P0 美国核心 |
| 4 | Cato Institute | 卡托研究所 | P1 美国扩展 |
| 5 | Center for Strategic and International Studies | 战略和国际问题研究中心 | P0 美国核心 |
| 6 | American Enterprise Institute | 美国企业研究所 | P1 美国扩展 |
| 7 | RAND Corporation | 兰德公司 | P0 美国核心 |
| 8 | Carnegie Endowment for International Peace | 卡内基国际和平基金会 | P0 美国核心 |
| 9 | Atlantic Council | 大西洋理事会 | P1 美国扩展 |
| 10 | Hoover Institution | 胡佛研究所 | P1 美国扩展 |
| 11 | Peterson Institute for International Economics (PIIE) | 彼得森国际经济研究所 | P0 美国核心 |
| 12 | Bruegel | 比利时布鲁盖尔研究所 | P2 英欧重点 |
| 13 | Chatham House | 英国皇家国际事务研究所 | P2 英欧重点 |
| 14 | Wilson Center | 威尔逊中心 | P1 美国扩展 |
| 15 | Center for American Progress | 美国进步中心 | P1 美国扩展 |
| 16 | National Bureau of Economic Research (NBER) | 美国国家经济研究局 | P1 美国扩展 |
| 17 | Centre for Economic Policy Research (CEPR) | 经济政策研究中心 | P2 英欧重点 |
| 18 | Leibniz Institute | 莱布尼茨研究所 | P2 英欧重点，需确认具体机构全称 |
| 19 | Peter G. Peterson Institute for International Economics (IIE) | 彼得森国际经济研究所，疑似 PIIE 重复项 | P0 美国核心，需去重 |
| 20 | German Institute / Deutsches Institut | 柏林德意志研究所，需确认具体机构全称 | P2 英欧重点 |
| 21 | Research Institute of Economy, Trade and Industry (RIETI) | 日本经济产业研究所 | P3 周边重点 |
| 22 | Economic Research Institute for ASEAN and East Asia (ERIA) | 东盟与东亚经济研究所 | P3 周边重点 |
| 23 | ifo Institute | 德国 ifo 经济研究所 | P2 英欧重点 |
| 24 | French Institute of International Relations (IFRI) | 法国国际关系研究所 | P2 英欧重点 |
| 25 | Japan Institute of International Affairs (JIIA) | 日本国际问题研究所 | P3 周边重点 |

## 二、与当前平台状态的关系

### 已进入或接近试运行的来源

| 来源 | 当前建议 |
| --- | --- |
| Brookings Institution | 已进入小批量试运行，继续保持每次最多新增 1 篇并人工复核 |
| Council on Foreign Relations | 已进入小批量试运行，继续保持 PDF 页数门槛 |
| Center for Strategic and International Studies | 已进入小批量试运行，仅保留主入口 |
| American Enterprise Institute | 已进入小批量试运行，允许网页长文但需人工把关 |
| Peterson Institute for International Economics | 已进入小批量试运行，继续执行 PDF 页数门槛 |
| Chatham House | 已有解析器试点，但仍需继续只读审计 |
| NBER | 已有解析器测试基础，可纳入下一批美国扩展来源 |
| ECFR | 虽不在 Word 重点名单中，但在 Top 100 PDF 中出现，已作为欧洲来源试点 |

### 需要重点补齐的美国来源

| 来源 | 建议动作 |
| --- | --- |
| RAND Corporation | 确认报告库入口，做只读审计 |
| Carnegie Endowment for International Peace | 确认报告与专题页入口，做只读审计 |
| Atlantic Council | 确认涉华专题和报告入口，做只读审计 |
| Hoover Institution | 确认报告入口，做只读审计 |
| Wilson Center | 确认 China / Asia 相关入口，做只读审计 |
| The Heritage Foundation | 当前不宜直接自动化，需确认稳定入口 |
| Cato Institute | 当前不宜直接自动化，需解决站点访问或入口问题 |
| Center for American Progress | 当前不宜直接自动化，需确认稳定入口 |

### 需要确认全称或去重的条目

| 条目 | 问题 |
| --- | --- |
| Leibniz Institute | 需要确认是 Leibniz Institute for Economic Research、Leibniz Centre for European Economic Research，还是其他具体机构 |
| German Institute / Deutsches Institut | 需要确认是 German Institute for International and Security Affairs (SWP)、German Development Institute (DIE) 还是其他机构 |
| Peter G. Peterson Institute for International Economics (IIE) | 与 PIIE 高度疑似重复，需要合并 |

## 三、Top 100 附件中的全球参考名单

以下名单来自 `think tank top 100.pdf`，可作为后续扩展来源池。PDF 原文存在少量排版问题，例如第 80 位重复出现、个别长名称被截断、Development Research Center 出现两次。后续入库前应再做人工校对。

| 排名 | 名称 | 国家或地区 |
| ---: | --- | --- |
| 1 | Brookings Institution | United States |
| 2 | Chatham House | United Kingdom |
| 3 | Carnegie Endowment for International Peace | United States |
| 4 | Center for Strategic and International Studies (CSIS) | United States |
| 5 | Bruegel | Belgium |
| 6 | Stockholm International Peace Research Institute (SIPRI) | Sweden |
| 7 | Rand Corporation | United States |
| 8 | Council on Foreign Relations (CFR) | United States |
| 9 | International Institute for Strategic Studies (IISS) | United Kingdom |
| 10 | Woodrow Wilson International Center for Scholars | United States |
| 11 | Amnesty International (AI) | United Kingdom |
| 12 | Transparency International (TI) | Germany |
| 13 | Japan Institute of International Affairs (JIIA) | Japan |
| 14 | German Institute for International and Security Affairs (SWP) | Germany |
| 15 | Peterson Institute for International Economics (PIIE) | United States |
| 16 | Cato Institute | United States |
| 17 | Heritage Foundation | United States |
| 18 | Fundacao Getulio Vargas (FGV) | Brazil |
| 19 | Fraser Institute | Canada |
| 20 | French Institute of International Relations (IFRI) | France |
| 21 | International Crisis Group (ICG) | Belgium |
| 22 | Centre for Economic Policy Research (CEPR) | United Kingdom |
| 23 | Centre for European Policy Studies (CEPS) | Belgium |
| 24 | American Enterprise Institute for Public Policy Research (AEI) | United States |
| 25 | Center for American Progress (CAP) | United States |
| 26 | Carnegie Moscow Center | Russia |
| 27 | Chinese Academy of Social Sciences (CASS) | China |
| 28 | Asian Development Bank Institute (ADBI) | Japan |
| 29 | Konrad Adenauer Foundation (KAS) | Germany |
| 30 | Friedrich Ebert Foundation (FES) | Germany |
| 31 | European Council on Foreign Relations (ECFR) | United Kingdom |
| 32 | Institute for World Economy and International Relations (IMEMO RAS) | Russia |
| 33 | German Council on Foreign Relations (DGAP) | Germany |
| 34 | Clingendael, Netherlands Institute of International Relations | Netherlands |
| 35 | Wilfried Martens Centre for European Studies | Belgium |
| 36 | China Institute of International Studies (CIIS) | China |
| 37 | Carnegie Middle East Center | Lebanon |
| 38 | Consejo Argentino para las Relaciones Internacionales (CARI) | Argentina |
| 39 | Danish Institute of International Studies (DIIS) | Denmark |
| 40 | China Institutes of Contemporary International Relations (CICIR) | China |
| 41 | Kiel Institute for the World Economy (IfW) | Germany |
| 42 | IDEAS | United Kingdom |
| 43 | Centre for International Governance Innovation (CIGI) | Canada |
| 44 | Royal United Services Institute (RUSI) | United Kingdom |
| 45 | Korea Institute for International Economic Policy (KIEP) | Republic of Korea |
| 46 | World Economic Forum (WEF) | Switzerland |
| 47 | Human Rights Watch (HRW) | United Kingdom |
| 48 | Development Research Center of the State Council (DRC) | China |
| 49 | Korea Development Institute (KDI) | Republic of Korea |
| 50 | Centre for Civil Society (CCS) | India |
| 51 | Al-Ahram Center for Political and Strategic Studies (ACPSS) | Egypt |
| 52 | Institute of Economic Affairs (IEA) | United Kingdom |
| 53 | Libertad y Desarrollo (LyD) | Chile |
| 54 | Lowy Institute for International Policy | Australia |
| 55 | Overseas Development Institute (ODI) | United Kingdom |
| 56 | Food, Agriculture and Natural Resources Policy Analysis Network | South Africa |
| 57 | Bonn International Center for Conversion (BICC) | Germany |
| 58 | Barcelona Centre for International Affairs (CIDOB) | Spain |
| 59 | Peace Research Institute Oslo (PRIO) | Norway |
| 60 | East Asia Institute (EAI) | Republic of Korea |
| 61 | IISS, FKA Center for International and Strategic Studies | China |
| 62 | African Economic Research Consortium (AERC) | Kenya |
| 63 | African Centre for the Constructive Resolution of Disputes (ACCORD) | South Africa |
| 64 | Razumkov Centre | Ukraine |
| 65 | RAND Europe | United Kingdom |
| 66 | Polish Institute of International Affairs (PISM) | Poland |
| 67 | Center for Social and Economic Research (CASE) | Poland |
| 68 | Demos | United Kingdom |
| 69 | Centre for Strategic and International Studies (CSIS) | Indonesia |
| 70 | Centre For European Reform (CER) | United Kingdom |
| 71 | Shanghai Institutes for International Studies (SIIS) | China |
| 72 | European Union Institute for Security Studies (EUISS) | France |
| 73 | Norwegian Institute of International Affairs (NUPI) | Norway |
| 74 | Turkish Economic and Social Studies Foundation (TESEV) | Turkey |
| 75 | European Centre for International Political Economy (ECIPE) | Belgium |
| 76 | Civitas Institute for the Study of Civil Society | United Kingdom |
| 77 | Institute of Foreign Affairs and National Security (IFANS) | Republic of Korea |
| 78 | Singapore Institute of International Affairs (SIIA) | Singapore |
| 79 | Fundacion para las Relaciones Internacionales y el Dialogo Exterior (FRIDE) | Spain |
| 80 | Institute of Defence and Strategic Studies (IDSS) | Singapore |
| 81 | South African Institute of International Affairs (SAIIA) | South Africa |
| 82 | German Development Institute (DIE) | Germany |
| 83 | Fundacion para el Analisis y los Estudios Sociales (FAES) | Spain |
| 84 | Centre for Conflict Resolution (CCR) | South Africa |
| 85 | Istituto Affari Internazionali (IAI) | Italy |
| 86 | Heinrich Boll Foundation (HBS) | Germany |
| 87 | Association for Liberal Thinking (ALT) | Turkey |
| 88 | Timbro | Sweden |
| 89 | Centre for Policy Studies (CPS) | United Kingdom |
| 90 | Centre for Public Policy Studies (CPPS) | Malaysia |
| 91 | Centro de Estudios Publicos (CEP) | Chile |
| 92 | Institute of Southeast Asian Studies (ISEAS) | Singapore |
| 93 | Institute of Development Studies (IDS) | United Kingdom |
| 94 | Real Instituto Elcano | Spain |
| 95 | Facultad Latinoamericana de Ciencias Sociales (FLACSO) | Costa Rica |
| 96 | African Technology Policy Studies Network (ATPS) | Kenya |
| 97 | Bangladesh Institute of Development Studies (BIDS) | Bangladesh |
| 98 | Council on Foreign and Defense Policy (SVOP) | Russia |
| 99 | Development Research Center of the State Council (DRC) | China |
| 100 | Institute for Defence Studies and Analyses (IDSA) | India |

## 四、建议接入顺序

### 第一批：老师重点美国来源补齐

继续稳定已接入来源，同时补齐以下来源的只读审计：

1. RAND Corporation
2. Carnegie Endowment for International Peace
3. Atlantic Council
4. Hoover Institution
5. Wilson Center
6. NBER

阻塞或不稳定来源继续保持人工确认：

1. The Heritage Foundation
2. Cato Institute
3. Center for American Progress

### 第二批：英欧重点来源

优先处理老师点名且在 Top 100 中排名靠前的来源：

1. Chatham House
2. Bruegel
3. CEPR
4. IFRI
5. SWP
6. DGAP
7. ECFR
8. ifo Institute

### 第三批：周边与亚太来源

优先处理日本、韩国、东盟和新加坡来源：

1. JIIA
2. RIETI
3. ERIA
4. KIEP
5. KDI
6. East Asia Institute
7. SIIA
8. ISEAS

## 五、下一步处理建议

1. 将本清单作为 `source-governance.md` 和种子数据更新依据。
2. 对老师重点名单中尚未稳定接入的来源逐一做只读审计。
3. 对全称不清或重复条目先向老师确认，再写入正式种子数据。
4. 每个新增来源都保留“候选发现、样本复核、准入结论”的记录。
