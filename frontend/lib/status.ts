export type ReportCrawlStatus = 'pending' | 'running' | 'success' | 'failed';

export type CrawlRunStatus = 'pending' | 'running' | 'success' | 'failed';

export type SourceCrawlStatus = 'never' | 'running' | 'success' | 'failed';

export type ReportAIStatus =
  | 'pending'
  | 'queued'
  | 'processing'
  | 'finalize_queued'
  | 'finalizing'
  | 'success'
  | 'failed'
  | 'skipped';

export type ReportReviewStatus =
  | 'pending_review'
  | 'approved'
  | 'needs_rerun'
  | 'rejected';

export type ReportContentKind = 'pdf' | 'web_article';

export type ReportDeliverableStatus = 'complete' | 'partial' | 'empty';

export type AIChunkType = 'translation' | 'analysis';

export type AIChunkStatus =
  | 'pending'
  | 'queued'
  | 'processing'
  | 'success'
  | 'failed';

export type SourceType = 'website' | 'rss' | 'report_library' | 'topic_page';

export type CrawlCandidateStatus = 'discovered' | 'skipped' | 'saved';

export type SourceHealthStatus =
  | 'healthy'
  | 'warning'
  | 'failed'
  | 'never'
  | 'disabled';

export type PriorityTier = 'P0' | 'P1' | 'P2' | 'P3' | 'P4';

export type RegionFocus =
  | 'us'
  | 'europe'
  | 'neighboring'
  | 'international'
  | 'domestic'
  | 'candidate';

export type NotificationEventType =
  | 'report.created'
  | 'report.ai_completed'
  | 'report.ai_failed'
  | 'report.fetch_failed'
  | 'report.review_needs_rerun'
  | 'daily_summary';

export const reportCrawlStatusLabels: Record<ReportCrawlStatus, string> = {
  pending: '待抓取',
  running: '抓取中',
  success: '已抓取',
  failed: '抓取失败',
};

export const reportAIStatusLabels: Record<ReportAIStatus, string> = {
  pending: '待处理',
  queued: 'AI 已入队',
  processing: 'AI 处理中',
  finalize_queued: '等待生成终稿',
  finalizing: '正在生成终稿',
  success: 'AI 已完成',
  failed: 'AI 失败',
  skipped: '已跳过',
};

export const reportReviewStatusLabels: Record<ReportReviewStatus, string> = {
  pending_review: '待复核',
  approved: '已通过',
  needs_rerun: '需重跑',
  rejected: '不采用',
};

export const reportContentKindLabels: Record<ReportContentKind, string> = {
  pdf: 'PDF 报告',
  web_article: '网页长文',
};

export const reportDeliverableStatusLabels: Record<
  ReportDeliverableStatus,
  string
> = {
  complete: '成果齐全',
  partial: '部分生成',
  empty: '尚无成果',
};

export const aiChunkTypeLabels: Record<AIChunkType, string> = {
  translation: '全文翻译',
  analysis: '分析笔记',
};

export const aiChunkStatusLabels: Record<AIChunkStatus, string> = {
  pending: '待处理',
  queued: '已入队',
  processing: '处理中',
  success: '成功',
  failed: '失败',
};

export const crawlRunStatusLabels: Record<CrawlRunStatus, string> = {
  pending: '等待中',
  running: '抓取中',
  success: '成功',
  failed: '失败',
};

export const sourceCrawlStatusLabels: Record<SourceCrawlStatus, string> = {
  never: '未抓取',
  running: '抓取中',
  success: '成功',
  failed: '失败',
};

export const crawlCandidateStatusLabels: Record<CrawlCandidateStatus, string> = {
  discovered: '已发现',
  skipped: '已跳过',
  saved: '已入库',
};

export const priorityTierLabels: Record<PriorityTier, string> = {
  P0: 'P0 美国核心',
  P1: 'P1 美国扩展',
  P2: 'P2 英欧重点',
  P3: 'P3 周边重点',
  P4: 'P4 待校对/补充',
};

export const regionFocusLabels: Record<RegionFocus, string> = {
  us: '美国',
  europe: '英欧',
  neighboring: '周边国家',
  international: '国际组织',
  domestic: '国内对照',
  candidate: '待校对池',
};

export const sourceTypeLabels: Record<SourceType, string> = {
  website: '网站',
  rss: 'RSS',
  report_library: '报告库',
  topic_page: '专题页',
};

export const notificationEventTypeLabels: Record<NotificationEventType, string> = {
  'report.created': '新报告入库',
  'report.ai_completed': 'AI 成果完成',
  'report.ai_failed': 'AI 处理失败',
  'report.fetch_failed': '正文抓取失败',
  'report.review_needs_rerun': '需重跑',
  daily_summary: '每日监测摘要',
};
