import { type Report } from '@/lib/report';
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

export function formatDateTime(value: string | null): string {
  if (!value) {
    return '未知';
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

export function formatShortDate(value: string | null): string {
  if (!value) {
    return '未知';
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
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
  return ['queued', 'processing', 'finalize_queued', 'finalizing'].includes(
    report.ai_status
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

  if (
    ['processing', 'finalize_queued', 'finalizing', 'queued'].includes(
      report.ai_status
    )
  ) {
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
