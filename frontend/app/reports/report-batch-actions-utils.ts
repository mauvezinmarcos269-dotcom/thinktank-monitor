import {
  reportReviewStatusLabels,
  type ReportReviewStatus,
} from '@/lib/status';
import { type ReportBatchExportFormat } from '@/lib/report';

type BatchActionLabelsInput = {
  busy: boolean;
  batchReviewStatus: ReportReviewStatus | '';
  selectedReportCount: number;
  visibleReportCount: number;
  visibleSelectedReportCount: number;
  allVisibleSelected: boolean;
  submittingBatchReview: boolean;
  exportingBatchFormat: ReportBatchExportFormat | null;
};

export type BatchActionLabels = {
  hasPartialSelection: boolean;
  otherPageSelectedCount: number;
  selectAllLabel: string;
  clearSelectionLabel: string;
  busyLabel: string;
  applyButtonLabel: string;
  batchReviewTargetLabel: string;
  markdownExportLabel: string;
  docxExportLabel: string;
};

export function getBatchReviewTargetClass(
  status: ReportReviewStatus | ''
): string {
  if (status === 'approved') {
    return 'batch-review-target-success';
  }

  if (status === 'needs_rerun') {
    return 'batch-review-target-warning';
  }

  if (status === 'rejected') {
    return 'batch-review-target-danger';
  }

  return '';
}

export function getBatchActionLabels({
  busy,
  batchReviewStatus,
  selectedReportCount,
  visibleReportCount,
  visibleSelectedReportCount,
  allVisibleSelected,
  submittingBatchReview,
  exportingBatchFormat,
}: BatchActionLabelsInput): BatchActionLabels {
  const isWaitingForOtherTask =
    busy && !submittingBatchReview && exportingBatchFormat === null;
  const hasPartialSelection =
    visibleSelectedReportCount > 0 &&
    visibleSelectedReportCount < visibleReportCount &&
    !allVisibleSelected;
  const otherPageSelectedCount =
    selectedReportCount - visibleSelectedReportCount;

  return {
    hasPartialSelection,
    otherPageSelectedCount,
    clearSelectionLabel:
      otherPageSelectedCount > 0 ? '清空全部选择' : '清空选择',
    selectAllLabel: getSelectAllLabel({
      allVisibleSelected,
      hasPartialSelection,
      visibleReportCount,
      visibleSelectedReportCount,
    }),
    busyLabel: getBusyLabel({
      submittingBatchReview,
      exportingBatchFormat,
      isWaitingForOtherTask,
    }),
    applyButtonLabel: getApplyButtonLabel({
      submittingBatchReview,
      exportingBatchFormat,
      isWaitingForOtherTask,
      batchReviewStatus,
      selectedReportCount,
    }),
    batchReviewTargetLabel: getBatchReviewTargetLabel({
      batchReviewStatus,
      selectedReportCount,
    }),
    markdownExportLabel: getExportButtonLabel({
      format: 'markdown',
      selectedReportCount,
      submittingBatchReview,
      exportingBatchFormat,
      isWaitingForOtherTask,
    }),
    docxExportLabel: getExportButtonLabel({
      format: 'docx',
      selectedReportCount,
      submittingBatchReview,
      exportingBatchFormat,
      isWaitingForOtherTask,
    }),
  };
}

function getSelectAllLabel({
  allVisibleSelected,
  hasPartialSelection,
  visibleReportCount,
  visibleSelectedReportCount,
}: {
  allVisibleSelected: boolean;
  hasPartialSelection: boolean;
  visibleReportCount: number;
  visibleSelectedReportCount: number;
}): string {
  if (allVisibleSelected) {
    return `已全选本页 ${visibleReportCount} 篇报告，点击取消本页选择`;
  }

  if (hasPartialSelection) {
    return `本页已选 ${visibleSelectedReportCount} / ${visibleReportCount} 篇报告，点击全选本页`;
  }

  return `本页未选择报告，点击全选本页 ${visibleReportCount} 篇报告`;
}

function getBusyLabel({
  submittingBatchReview,
  exportingBatchFormat,
  isWaitingForOtherTask,
}: {
  submittingBatchReview: boolean;
  exportingBatchFormat: ReportBatchExportFormat | null;
  isWaitingForOtherTask: boolean;
}): string {
  if (submittingBatchReview) {
    return '批量复核处理中';
  }

  if (exportingBatchFormat === 'markdown') {
    return 'Markdown 导出中';
  }

  if (exportingBatchFormat === 'docx') {
    return 'Word 导出中';
  }

  return isWaitingForOtherTask ? '其他任务处理中' : '';
}

function getApplyButtonLabel({
  submittingBatchReview,
  exportingBatchFormat,
  isWaitingForOtherTask,
  batchReviewStatus,
  selectedReportCount,
}: {
  submittingBatchReview: boolean;
  exportingBatchFormat: ReportBatchExportFormat | null;
  isWaitingForOtherTask: boolean;
  batchReviewStatus: ReportReviewStatus | '';
  selectedReportCount: number;
}): string {
  if (submittingBatchReview) {
    return '处理中……';
  }

  if (exportingBatchFormat !== null || isWaitingForOtherTask) {
    return '等待中';
  }

  if (batchReviewStatus && selectedReportCount > 0) {
    return `应用（${selectedReportCount}）`;
  }

  return '应用';
}

function getBatchReviewTargetLabel({
  batchReviewStatus,
  selectedReportCount,
}: {
  batchReviewStatus: ReportReviewStatus | '';
  selectedReportCount: number;
}): string {
  if (!batchReviewStatus) {
    return '';
  }

  if (selectedReportCount > 0) {
    return `将 ${selectedReportCount} 篇标记为：${
      reportReviewStatusLabels[batchReviewStatus]
    }`;
  }

  return `将标记为：${reportReviewStatusLabels[batchReviewStatus]}`;
}

function getExportButtonLabel({
  format,
  selectedReportCount,
  submittingBatchReview,
  exportingBatchFormat,
  isWaitingForOtherTask,
}: {
  format: ReportBatchExportFormat;
  selectedReportCount: number;
  submittingBatchReview: boolean;
  exportingBatchFormat: ReportBatchExportFormat | null;
  isWaitingForOtherTask: boolean;
}): string {
  if (exportingBatchFormat === format) {
    return '导出中……';
  }

  if (
    submittingBatchReview ||
    (exportingBatchFormat !== null && exportingBatchFormat !== format) ||
    isWaitingForOtherTask
  ) {
    return '等待中';
  }

  const formatLabel = format === 'markdown' ? 'Markdown' : 'Word';
  if (selectedReportCount > 0) {
    return `导出 ${formatLabel}（${selectedReportCount}）`;
  }

  return `导出 ${formatLabel}`;
}
