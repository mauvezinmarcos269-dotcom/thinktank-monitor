'use client';

import { type Source, type ThinkTank } from '@/lib/institution';
import {
  type Report,
  type ReportBatchExportFormat,
} from '@/lib/report';
import {
  type ReportAIStatus,
  type ReportContentKind,
  type ReportDeliverableStatus,
  type ReportReviewStatus,
} from '@/lib/status';

import { ReportBatchActions } from './report-batch-actions';
import { ReportFilterBar } from './report-filter-bar';
import { ReportList } from './report-list';
import { type ReportWorkflowShortcut } from './report-filter-bar';

type ReportListPanelProps = {
  reports: Report[];
  sourcesById: Map<number, Source>;
  thinkTanksById: Map<number, ThinkTank>;
  selectedReportIds: Set<number>;
  activeReportId: number | null;
  canRetryAI: boolean;
  loadingList: boolean;
  isReportListBusy: boolean;
  reportListBusyMessage: string;
  submittingAIReportId: number | null;
  searchDraft: string;
  keywordFilter: string;
  totalReports: number;
  page: number;
  totalPages: number;
  reviewStatusFilter: ReportReviewStatus | '';
  aiStatusFilter: ReportAIStatus | '';
  contentKindFilter: ReportContentKind | '';
  deliverableStatusFilter: ReportDeliverableStatus | '';
  thinkTankFilter: number | '';
  sourceFilter: number | '';
  thinkTanks: ThinkTank[];
  sourceOptions: Source[];
  visibleSelectedReportCount: number;
  allVisibleSelected: boolean;
  batchReviewStatus: ReportReviewStatus | '';
  submittingBatchReview: boolean;
  exportingBatchFormat: ReportBatchExportFormat | null;
  onSearchDraftChange: (value: string) => void;
  onSearchSubmit: () => void;
  onSearchClear: () => void;
  onResetFilters: () => void;
  onReviewStatusChange: (value: ReportReviewStatus | '') => void;
  onAIStatusChange: (value: ReportAIStatus | '') => void;
  onContentKindChange: (value: ReportContentKind | '') => void;
  onDeliverableStatusChange: (value: ReportDeliverableStatus | '') => void;
  onThinkTankChange: (value: number | '') => void;
  onSourceChange: (value: number | '') => void;
  onWorkflowShortcut: (shortcut: ReportWorkflowShortcut) => void;
  onPreviousPage: () => void;
  onNextPage: () => void;
  onToggleAllVisible: () => void;
  onClearSelection: () => void;
  onBatchReviewStatusChange: (value: ReportReviewStatus | '') => void;
  onApplyBatchReview: () => void;
  onBatchExport: (format: ReportBatchExportFormat) => void;
  onSelectReport: (reportId: number) => void;
  onToggleReportSelection: (reportId: number) => void;
  onRetryAI: (reportId: number) => void;
};

export function ReportListPanel({
  reports,
  sourcesById,
  thinkTanksById,
  selectedReportIds,
  activeReportId,
  canRetryAI,
  loadingList,
  isReportListBusy,
  reportListBusyMessage,
  submittingAIReportId,
  searchDraft,
  keywordFilter,
  totalReports,
  page,
  totalPages,
  reviewStatusFilter,
  aiStatusFilter,
  contentKindFilter,
  deliverableStatusFilter,
  thinkTankFilter,
  sourceFilter,
  thinkTanks,
  sourceOptions,
  visibleSelectedReportCount,
  allVisibleSelected,
  batchReviewStatus,
  submittingBatchReview,
  exportingBatchFormat,
  onSearchDraftChange,
  onSearchSubmit,
  onSearchClear,
  onResetFilters,
  onReviewStatusChange,
  onAIStatusChange,
  onContentKindChange,
  onDeliverableStatusChange,
  onThinkTankChange,
  onSourceChange,
  onWorkflowShortcut,
  onPreviousPage,
  onNextPage,
  onToggleAllVisible,
  onClearSelection,
  onBatchReviewStatusChange,
  onApplyBatchReview,
  onBatchExport,
  onSelectReport,
  onToggleReportSelection,
  onRetryAI,
}: ReportListPanelProps) {
  return (
    <section className="panel report-list-panel">
      <div className="report-list-controls">
        <ReportFilterBar
          searchDraft={searchDraft}
          keywordFilter={keywordFilter}
          loading={loadingList || isReportListBusy}
          busyMessage={reportListBusyMessage}
          totalReports={totalReports}
          page={page}
          totalPages={totalPages}
          reviewStatusFilter={reviewStatusFilter}
          aiStatusFilter={aiStatusFilter}
          contentKindFilter={contentKindFilter}
          deliverableStatusFilter={deliverableStatusFilter}
          thinkTankFilter={thinkTankFilter}
          sourceFilter={sourceFilter}
          thinkTanks={thinkTanks}
          sourceOptions={sourceOptions}
          onSearchDraftChange={onSearchDraftChange}
          onSearchSubmit={onSearchSubmit}
          onSearchClear={onSearchClear}
          onResetFilters={onResetFilters}
          onReviewStatusChange={onReviewStatusChange}
          onAIStatusChange={onAIStatusChange}
          onContentKindChange={onContentKindChange}
          onDeliverableStatusChange={onDeliverableStatusChange}
          onThinkTankChange={onThinkTankChange}
          onSourceChange={onSourceChange}
          onWorkflowShortcut={onWorkflowShortcut}
          onPreviousPage={onPreviousPage}
          onNextPage={onNextPage}
        />

        {canRetryAI && (
          <ReportBatchActions
            visibleReportCount={reports.length}
            selectedReportCount={selectedReportIds.size}
            visibleSelectedReportCount={visibleSelectedReportCount}
            allVisibleSelected={allVisibleSelected}
            loadingList={loadingList}
            busy={isReportListBusy}
            batchReviewStatus={batchReviewStatus}
            submittingBatchReview={submittingBatchReview}
            exportingBatchFormat={exportingBatchFormat}
            onToggleAllVisible={onToggleAllVisible}
            onClearSelection={onClearSelection}
            onBatchReviewStatusChange={onBatchReviewStatusChange}
            onApplyBatchReview={onApplyBatchReview}
            onBatchExport={onBatchExport}
          />
        )}
      </div>

      <ReportList
        reports={reports}
        sourcesById={sourcesById}
        thinkTanksById={thinkTanksById}
        selectedReportIds={selectedReportIds}
        activeReportId={activeReportId}
        canRetryAI={canRetryAI}
        selectionDisabled={isReportListBusy}
        submittingAIReportId={submittingAIReportId}
        onSelectReport={onSelectReport}
        onToggleReportSelection={onToggleReportSelection}
        onRetryAI={onRetryAI}
        onResetFilters={onResetFilters}
      />
    </section>
  );
}
