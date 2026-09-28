import {
  type Report,
  type ReportBatchExportFormat,
} from '@/lib/report';
import {
  reportReviewStatusLabels,
  type ReportAIStatus,
  type ReportContentKind,
  type ReportReviewStatus,
} from '@/lib/status';

export type ReportView = 'content' | 'translation' | 'summary' | 'commentary';
export type CopyTarget = 'commentary' | 'translation' | 'current';

export type ReportWorkflowState = {
  label: string;
  className: string;
  hint: string;
};

export type ReportListBusyState = {
  isReportListBusy: boolean;
  reportListBusyMessage: string;
};

export const reportViewKeys: ReportView[] = [
  'content',
  'translation',
  'summary',
  'commentary',
];

export const reportViews: Array<{
  key: ReportView;
  label: string;
  emptyText: string;
}> = [
  {
    key: 'content',
    label: '原文正文',
    emptyText: '暂无正文，请先抓取正文。',
  },
  {
    key: 'translation',
    label: '全文翻译',
    emptyText: '暂无全文翻译，等待 AI 处理完成。',
  },
  {
    key: 'summary',
    label: '主要观点',
    emptyText: '暂无主要观点，等待 AI 处理完成。',
  },
  {
    key: 'commentary',
    label: '深层研判',
    emptyText: '暂无深层研判，等待 AI 处理完成。',
  },
];

export const PAGE_SIZE = 20;

export const reviewStatusOptions: ReportReviewStatus[] = [
  'pending_review',
  'approved',
  'needs_rerun',
  'rejected',
];

export const aiStatusOptions: ReportAIStatus[] = [
  'pending',
  'queued',
  'processing',
  'finalize_queued',
  'finalizing',
  'success',
  'failed',
  'skipped',
];

export const contentKindOptions: ReportContentKind[] = [
  'pdf',
  'web_article',
];

const aiProcessingStatuses = [
  'queued',
  'processing',
  'finalize_queued',
  'finalizing',
] as const;

export function getInitialView(value: string | null): ReportView {
  if (value && reportViewKeys.includes(value as ReportView)) {
    return value as ReportView;
  }

  return 'content';
}

export function getPreferredReportView(
  report: Report,
  value: string | null
): ReportView {
  if (value && reportViewKeys.includes(value as ReportView)) {
    return value as ReportView;
  }

  if (report.summary?.trim()) {
    return 'summary';
  }

  if (report.commentary?.trim()) {
    return 'commentary';
  }

  if (report.translation?.trim()) {
    return 'translation';
  }

  return 'content';
}

function parseDateTime(value: string | null): Date | null {
  if (!value) {
    return null;
  }

  const date = new Date(value);

  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDateTime(value: string | null): string {
  const date = parseDateTime(value);

  return date ? date.toLocaleString() : value || '未知';
}

export function formatShortDate(value: string | null): string {
  const date = parseDateTime(value);

  if (!date) {
    return value || '未知';
  }

  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}

export function countTextChars(value: string | null): number {
  return value?.trim().length ?? 0;
}

export function buildCommentaryText(report: Report): string {
  return [
    '第一部分：主要观点',
    report.summary?.trim() || '暂无主要观点。',
    '',
    '第二部分：深层研判',
    report.commentary?.trim() || '暂无深层研判。',
  ].join('\n');
}

export function getDocumentType(report: Report): {
  label: string;
  className: string;
  isPdf: boolean;
} {
  const isPdf =
    report.content_kind === 'pdf'
    || (!report.content_kind && Boolean(report.pdf_url || report.page_count));

  return {
    label: isPdf ? 'PDF 报告' : '网页长文',
    className: isPdf ? 'badge badge-success' : 'badge badge-info',
    isPdf,
  };
}

export function isAIProcessing(report: Report): boolean {
  return aiProcessingStatuses.includes(
    report.ai_status as (typeof aiProcessingStatuses)[number]
  );
}

export function formatSourceUrl(value: string): string {
  try {
    const url = new URL(value);
    return url.hostname.replace(/^www\./, '');
  } catch {
    return value;
  }
}

export function getReviewHistorySummary(
  reviewEvents: Array<{
    review_status: ReportReviewStatus;
    created_at: string;
  }>,
  loading: boolean,
  errorMessage: string | null
): string {
  if (loading) {
    return '加载中';
  }

  if (errorMessage) {
    return '读取失败';
  }

  if (reviewEvents.length === 0) {
    return '暂无记录';
  }

  const latestEvent = reviewEvents.reduce((latest, event) =>
    new Date(event.created_at).getTime() > new Date(latest.created_at).getTime()
      ? event
      : latest
  );
  const latestStatus =
    reportReviewStatusLabels[latestEvent.review_status] ??
    latestEvent.review_status;

  return `最近：${latestStatus} · ${formatDateTime(latestEvent.created_at)}`;
}

export function getAIProgressSummary(
  progress: {
    total_chunks: number;
    completed_chunks: number;
    failed_chunks: number;
    running_chunks: number;
  } | null,
  loading: boolean,
  errorMessage: string | null
): string {
  if (loading) {
    return '加载中';
  }

  if (errorMessage) {
    return '读取失败';
  }

  if (!progress) {
    return '暂无记录';
  }

  if (progress.total_chunks === 0) {
    return '暂无分块';
  }

  const base = `${progress.completed_chunks}/${progress.total_chunks} 完成`;

  if (progress.failed_chunks > 0) {
    return `${base} · ${progress.failed_chunks} 失败`;
  }

  if (progress.running_chunks > 0) {
    return `${base} · ${progress.running_chunks} 运行中`;
  }

  return `${base} · 无失败`;
}

export function getReportListBusyState({
  submittingAIReportId,
  submittingBatchReview,
  exportingBatchFormat,
}: {
  submittingAIReportId: number | null;
  submittingBatchReview: boolean;
  exportingBatchFormat: ReportBatchExportFormat | null;
}): ReportListBusyState {
  if (submittingAIReportId !== null) {
    return {
      isReportListBusy: true,
      reportListBusyMessage: 'AI 任务提交中，暂不可切换筛选。',
    };
  }

  if (submittingBatchReview) {
    return {
      isReportListBusy: true,
      reportListBusyMessage: '批量复核处理中，暂不可切换筛选。',
    };
  }

  if (exportingBatchFormat !== null) {
    return {
      isReportListBusy: true,
      reportListBusyMessage: '批量导出中，暂不可切换筛选。',
    };
  }

  return {
    isReportListBusy: false,
    reportListBusyMessage: '',
  };
}

export function getReportWorkflowState(report: Report): ReportWorkflowState {
  if (report.review_status === 'approved') {
    return {
      label: '已通过复核',
      className: 'badge badge-success',
      hint: '成果已可用于阅读、下载和归档。',
    };
  }

  if (report.review_status === 'needs_rerun') {
    return {
      label: '需重新处理',
      className: 'badge badge-warning',
      hint: '老师已标记需重跑，请先查看复核意见。',
    };
  }

  if (report.review_status === 'rejected') {
    return {
      label: '不采用',
      className: 'badge badge-danger',
      hint: '该报告已被标记为不采用。',
    };
  }

  if (report.ai_status === 'success') {
    return {
      label: '待老师复核',
      className: 'badge badge-info',
      hint: 'AI 成果已生成，建议先阅读主要观点和深层研判。',
    };
  }

  if (isAIProcessing(report)) {
    return {
      label: '正在生成成果',
      className: 'badge badge-warning',
      hint: '系统正在处理翻译和评论稿，请稍后查看。',
    };
  }

  return {
    label: reportReviewStatusLabels[report.review_status] ?? '待处理',
    className: 'badge',
    hint: '成果尚未完整生成，可在下方折叠区查看处理细节。',
  };
}
