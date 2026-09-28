'use client';

import { type Source, type ThinkTank } from '@/lib/institution';
import { type Report } from '@/lib/report';
import {
  reportAIStatusLabels,
  reportCrawlStatusLabels,
  sourceTypeLabels,
} from '@/lib/status';

import {
  countTextChars,
  formatShortDate,
  formatSourceUrl,
  getDocumentType,
  getReportWorkflowState,
  isAIProcessing,
} from './report-page-utils';

type ReportListItemProps = {
  report: Report;
  source: Source | undefined;
  thinkTank: ThinkTank | null;
  selected: boolean;
  active: boolean;
  canRetryAI: boolean;
  selectionDisabled: boolean;
  submittingAIReportId: number | null;
  onSelectReport: (reportId: number) => void;
  onToggleReportSelection: (reportId: number) => void;
  onRetryAI: (reportId: number) => void;
};

function getCrawlMetaClass(status: Report['crawl_status']): string {
  if (status === 'success') {
    return 'report-list-meta-success';
  }

  if (status === 'failed') {
    return 'report-list-meta-danger';
  }

  if (status === 'running') {
    return 'report-list-meta-warning';
  }

  return '';
}

function getAIMetaClass(status: Report['ai_status']): string {
  if (status === 'success') {
    return 'report-list-meta-success';
  }

  if (status === 'failed') {
    return 'report-list-meta-danger';
  }

  if (
    ['queued', 'processing', 'finalize_queued', 'finalizing'].includes(status)
  ) {
    return 'report-list-meta-warning';
  }

  return '';
}

function getReviewNotePreview(value: string | null): string {
  const note = value?.replace(/\s+/g, ' ').trim();

  if (!note) {
    return '';
  }

  return note.length > 80 ? `${note.slice(0, 80)}...` : note;
}

function getDeliverableMetaClass(completedCount: number): string {
  if (completedCount === 3) {
    return 'report-list-meta-success';
  }

  if (completedCount > 0) {
    return 'report-list-meta-warning';
  }

  return 'report-list-meta-muted';
}

function getDeliverableMetaTitle(
  items: { label: string; ready: boolean }[]
): string {
  const readyLabels = items
    .filter((item) => item.ready)
    .map((item) => item.label);
  const missingLabels = items
    .filter((item) => !item.ready)
    .map((item) => item.label);

  if (missingLabels.length === 0) {
    return `成果已齐全：${readyLabels.join('、')}`;
  }

  if (readyLabels.length === 0) {
    return `成果尚未生成：${missingLabels.join('、')}`;
  }

  return `已生成：${readyLabels.join('、')}；待生成：${missingLabels.join('、')}`;
}

export function ReportListItem({
  report,
  source,
  thinkTank,
  selected,
  active,
  canRetryAI,
  selectionDisabled,
  submittingAIReportId,
  onSelectReport,
  onToggleReportSelection,
  onRetryAI,
}: ReportListItemProps) {
  const documentType = getDocumentType(report);
  const workflow = getReportWorkflowState(report);
  const dateLabel = report.published_at
    ? `发布：${formatShortDate(report.published_at)}`
    : `入库：${formatShortDate(report.created_at)}`;
  const hasContentText = countTextChars(report.content) > 0;
  const deliverableItems = [
    {
      label: '主要观点',
      ready: countTextChars(report.summary) > 0,
    },
    {
      label: '深层研判',
      ready: countTextChars(report.commentary) > 0,
    },
    {
      label: '全文翻译',
      ready: countTextChars(report.translation) > 0,
    },
  ];
  const deliverableCount = deliverableItems.filter((item) => item.ready).length;
  const deliverableTitle = getDeliverableMetaTitle(deliverableItems);
  const reviewNotePreview = getReviewNotePreview(report.review_note);
  const sourceLabel = [
    thinkTank?.name ?? '未知智库',
    source ? sourceTypeLabels[source.source_type] ?? source.source_type : '未知来源',
    source ? formatSourceUrl(source.url) : '',
  ]
    .filter(Boolean)
    .join(' / ');
  const sourceTitle = source ? `${sourceLabel} / ${source.url}` : sourceLabel;
  const isSubmittingCurrentAI = submittingAIReportId === report.id;
  const isSubmittingOtherAI =
    submittingAIReportId !== null && !isSubmittingCurrentAI;
  const isCurrentAIProcessing = isAIProcessing(report);
  const retryAIButtonLabel = isSubmittingCurrentAI
    ? '提交中'
    : isSubmittingOtherAI
      ? '等待中'
      : isCurrentAIProcessing
        ? (reportAIStatusLabels[report.ai_status] ?? report.ai_status)
        : '重跑';
  const itemClasses = [
    'report-list-item',
    canRetryAI ? 'report-list-item-selectable' : '',
    report.review_status === 'needs_rerun' ? 'report-list-item-warning' : '',
    active ? 'report-list-item-active' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <li className={itemClasses}>
      {canRetryAI && (
        <input
          type="checkbox"
          className="report-list-check"
          checked={selected}
          onChange={() => onToggleReportSelection(report.id)}
          disabled={selectionDisabled}
          aria-label={`选择报告：${report.title}`}
        />
      )}
      <button
        type="button"
        className="report-list-main"
        onClick={() => onSelectReport(report.id)}
        aria-current={active ? 'true' : undefined}
      >
        <span className="report-id-badge">ID {report.id}</span>
        <span className="report-title" title={report.title}>
          {report.title}
        </span>
        <span className={documentType.className}>{documentType.label}</span>
        <span className={workflow.className}>{workflow.label}</span>
        <span className="report-source-line" title={sourceTitle}>
          {sourceLabel}
        </span>
        <span className="report-workflow-hint">{workflow.hint}</span>
        <span className="report-list-meta">
          <small>{dateLabel}</small>
          <small className={getCrawlMetaClass(report.crawl_status)}>
            抓取：
            {reportCrawlStatusLabels[report.crawl_status] ??
              report.crawl_status}
          </small>
          <small className={getAIMetaClass(report.ai_status)}>
            AI：{reportAIStatusLabels[report.ai_status] ?? report.ai_status}
          </small>
          <small
            className={getDeliverableMetaClass(deliverableCount)}
            title={deliverableTitle}
          >
            成果：{deliverableCount}/3
          </small>
          {reviewNotePreview ? (
            <small
              className="report-list-meta-info"
              title={`复核意见：${reviewNotePreview}`}
            >
              复核意见
            </small>
          ) : null}
        </span>
      </button>
      {canRetryAI &&
        report.review_status === 'needs_rerun' &&
        report.crawl_status === 'success' &&
        hasContentText && (
          <button
            type="button"
            className="report-list-action"
            onClick={() => onRetryAI(report.id)}
            disabled={
              isSubmittingCurrentAI || isSubmittingOtherAI || isCurrentAIProcessing
            }
          >
            {retryAIButtonLabel}
          </button>
        )}
    </li>
  );
}
