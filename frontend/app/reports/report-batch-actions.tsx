'use client';

import {
  useEffect,
  useRef,
} from 'react';

import {
  reportReviewStatusLabels,
  type ReportReviewStatus,
} from '@/lib/status';

import {
  reviewStatusOptions,
} from './report-page-utils';
import { type ReportBatchExportFormat } from '@/lib/report';

type ReportBatchActionsProps = {
  visibleReportCount: number;
  selectedReportCount: number;
  visibleSelectedReportCount: number;
  allVisibleSelected: boolean;
  loadingList: boolean;
  busy: boolean;
  batchReviewStatus: ReportReviewStatus | '';
  submittingBatchReview: boolean;
  exportingBatchFormat: ReportBatchExportFormat | null;
  onToggleAllVisible: () => void;
  onClearSelection: () => void;
  onBatchReviewStatusChange: (value: ReportReviewStatus | '') => void;
  onApplyBatchReview: () => void;
  onBatchExport: (format: ReportBatchExportFormat) => void;
};

function getBatchReviewTargetClass(status: ReportReviewStatus | ''): string {
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

export function ReportBatchActions({
  visibleReportCount,
  selectedReportCount,
  visibleSelectedReportCount,
  allVisibleSelected,
  loadingList,
  busy,
  batchReviewStatus,
  submittingBatchReview,
  exportingBatchFormat,
  onToggleAllVisible,
  onClearSelection,
  onBatchReviewStatusChange,
  onApplyBatchReview,
  onBatchExport,
}: ReportBatchActionsProps) {
  const selectAllRef = useRef<HTMLInputElement | null>(null);
  const isWaitingForOtherTask =
    busy && !submittingBatchReview && exportingBatchFormat === null;
  const hasPartialSelection =
    visibleSelectedReportCount > 0 &&
    visibleSelectedReportCount < visibleReportCount &&
    !allVisibleSelected;
  const otherPageSelectedCount =
    selectedReportCount - visibleSelectedReportCount;
  const clearSelectionLabel =
    otherPageSelectedCount > 0 ? '清空全部选择' : '清空选择';
  const selectAllLabel = allVisibleSelected
    ? `已全选本页 ${visibleReportCount} 篇报告，点击取消本页选择`
    : hasPartialSelection
      ? `本页已选 ${visibleSelectedReportCount} / ${visibleReportCount} 篇报告，点击全选本页`
      : `本页未选择报告，点击全选本页 ${visibleReportCount} 篇报告`;
  const busyLabel = submittingBatchReview
    ? '批量复核处理中'
    : exportingBatchFormat === 'markdown'
      ? 'Markdown 导出中'
      : exportingBatchFormat === 'docx'
        ? 'Word 导出中'
        : isWaitingForOtherTask
          ? '其他任务处理中'
          : '';
  const applyButtonLabel = submittingBatchReview
    ? '处理中……'
    : exportingBatchFormat !== null || isWaitingForOtherTask
      ? '等待中'
      : batchReviewStatus && selectedReportCount > 0
        ? `应用（${selectedReportCount}）`
      : '应用';
  const batchReviewTargetLabel =
    batchReviewStatus && selectedReportCount > 0
      ? `将 ${selectedReportCount} 篇标记为：${
          reportReviewStatusLabels[batchReviewStatus]
        }`
      : batchReviewStatus
        ? `将标记为：${reportReviewStatusLabels[batchReviewStatus]}`
        : '';
  const markdownExportLabel =
    exportingBatchFormat === 'markdown'
      ? '导出中……'
      : submittingBatchReview ||
          exportingBatchFormat === 'docx' ||
          isWaitingForOtherTask
        ? '等待中'
        : selectedReportCount > 0
          ? `导出 Markdown（${selectedReportCount}）`
          : '导出 Markdown';
  const docxExportLabel =
    exportingBatchFormat === 'docx'
      ? '导出中……'
      : submittingBatchReview ||
          exportingBatchFormat === 'markdown' ||
          isWaitingForOtherTask
        ? '等待中'
        : selectedReportCount > 0
          ? `导出 Word（${selectedReportCount}）`
          : '导出 Word';

  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = hasPartialSelection;
    }
  }, [hasPartialSelection]);

  return (
    <div className="batch-action-bar">
      <div className="batch-selection-group">
        <label className="inline-check">
          <input
            ref={selectAllRef}
            type="checkbox"
            checked={allVisibleSelected}
            onChange={onToggleAllVisible}
            disabled={visibleReportCount === 0 || loadingList || busy}
            aria-label={selectAllLabel}
            aria-checked={hasPartialSelection ? 'mixed' : allVisibleSelected}
          />
          本页全选
        </label>
        <span className="muted">
          本页 {visibleReportCount} 篇，已选本页 {visibleSelectedReportCount}{' '}
          篇 / 总已选 {selectedReportCount} 篇
        </span>
        {otherPageSelectedCount > 0 && (
          <span className="batch-cross-page-note">
            含其他页 {otherPageSelectedCount} 篇
          </span>
        )}
        {selectedReportCount > 0 && (
          <button
            type="button"
            onClick={onClearSelection}
            disabled={busy}
            title={`清空当前已选的 ${selectedReportCount} 篇报告`}
          >
            {clearSelectionLabel}
          </button>
        )}
        {busy && <span className="batch-busy-note">{busyLabel}</span>}
      </div>

      <div className="batch-command-group">
        <select
          value={batchReviewStatus}
          onChange={(event) =>
            onBatchReviewStatusChange(
              event.target.value as ReportReviewStatus | ''
            )
          }
          disabled={submittingBatchReview || busy}
        >
          <option value="">批量复核</option>
          {reviewStatusOptions
            .filter((status) => status !== 'pending_review')
            .map((status) => (
              <option key={status} value={status}>
                {reportReviewStatusLabels[status]}
              </option>
            ))}
        </select>
        {batchReviewStatus && (
          <span
            className={[
              'batch-review-target',
              getBatchReviewTargetClass(batchReviewStatus),
            ].join(' ')}
          >
            {batchReviewTargetLabel}
          </span>
        )}
        <button
          type="button"
          onClick={onApplyBatchReview}
          disabled={
            submittingBatchReview ||
            busy ||
            !batchReviewStatus ||
            selectedReportCount === 0
          }
        >
          {applyButtonLabel}
        </button>
        <button
          type="button"
          onClick={() => onBatchExport('markdown')}
          disabled={
            exportingBatchFormat !== null || busy || selectedReportCount === 0
          }
        >
          {markdownExportLabel}
        </button>
        <button
          type="button"
          onClick={() => onBatchExport('docx')}
          disabled={
            exportingBatchFormat !== null || busy || selectedReportCount === 0
          }
        >
          {docxExportLabel}
        </button>
      </div>
    </div>
  );
}
