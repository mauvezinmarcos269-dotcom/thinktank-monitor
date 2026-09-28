'use client';

import {
  Suspense,
  useState,
} from 'react';
import { useSearchParams } from 'next/navigation';

import { AppShell } from '@/components/app-shell';
import { type Report } from '@/lib/report';
import { ReportDetailPanel } from './report-detail-panel';
import { ReportListPanel } from './report-list-panel';
import {
  getAIProgressSummary,
  getReportListBusyState,
  getReviewHistorySummary,
  PAGE_SIZE,
} from './report-page-utils';
import { useCurrentUser } from './use-current-user';
import { useReportActions } from './use-report-actions';
import { useReportDetail } from './use-report-detail';
import { useReportFilters } from './use-report-filters';
import { useReportInstitutions } from './use-report-institutions';
import { useReportList } from './use-report-list';
import { useReportPageDerived } from './use-report-page-derived';
import { useReportSelection } from './use-report-selection';
import { useReviewFocus } from './use-review-focus';

function ReportsPageContent() {
  const searchParams = useSearchParams();
  const [reports, setReports] = useState<Report[]>([]);

  const [listError, setListError] = useState<string | null>(null);
  const [taskMessage, setTaskMessage] = useState<string | null>(null);

  const currentUser = useCurrentUser();
  const {
    thinkTanks,
    sources,
  } = useReportInstitutions(setListError);
  const {
    selectedReportIds,
    setSelectedReportIds,
    visibleSelectedReportCount,
    allVisibleSelected,
    toggleReportSelection,
    toggleAllVisibleReports,
    clearReportSelection,
  } = useReportSelection(reports);
  const {
    selected,
    setSelected,
    aiProgress,
    reviewEvents,
    activeView,
    setActiveView,
    reviewNoteDraft,
    setReviewNoteDraft,
    detailError,
    setDetailError,
    progressError,
    reviewEventsError,
    loadingDetail,
    loadingProgress,
    loadingReviewEvents,
    submittingFetch,
    submittingAIReportId,
    loadReviewEvents,
    handleSelect,
    handleFetchContent,
    submitRetryAI,
    handleRetryAI,
    resetReportListState,
  } = useReportDetail({
    setReports,
    setSelectedReportIds,
    setTaskMessage,
  });
  const {
    page,
    setPage,
    reviewStatusFilter,
    aiStatusFilter,
    contentKindFilter,
    deliverableStatusFilter,
    searchDraft,
    keywordFilter,
    thinkTankFilter,
    sourceFilter,
    setSearchDraft,
    handleReviewStatusFilterChange,
    handleAIStatusFilterChange,
    handleContentKindFilterChange,
    handleDeliverableStatusFilterChange,
    handleSearchSubmit,
    handleSearchClear,
    handleResetFilters,
    handleThinkTankFilterChange,
    handleSourceFilterChange,
    handleWorkflowShortcut,
  } = useReportFilters(resetReportListState);
  const {
    totalReports,
    loadingList,
  } = useReportList({
    page,
    reviewStatusFilter,
    aiStatusFilter,
    contentKindFilter,
    deliverableStatusFilter,
    keywordFilter,
    thinkTankFilter,
    sourceFilter,
    focusedReportId: Number(searchParams.get('report_id')),
    setReports,
    setListError,
    setSelectedReportIds,
    handleSelect,
  });

  const canFetchContent = currentUser?.role === 'admin';
  const canRetryAI = currentUser?.role === 'admin';
  const {
    sourceOptions,
    sourceById,
    thinkTankById,
    selectedDocumentType,
    selectedSource,
    selectedThinkTank,
    adminDetailsSummary,
    aiActionLabel,
  } = useReportPageDerived({
    selected,
    sources,
    thinkTanks,
    thinkTankFilter,
  });
  const reviewHistorySummary = getReviewHistorySummary(
    reviewEvents,
    loadingReviewEvents,
    reviewEventsError
  );
  const aiProgressSummary = getAIProgressSummary(
    aiProgress,
    loadingProgress,
    progressError
  );
  const {
    reviewSectionRef,
    highlightReviewSection,
    openReviewDetails,
  } = useReviewFocus({
    selected,
    searchParams,
  });

  const {
    exportingReport,
    exportingDocx,
    exportingBatchFormat,
    copyingTarget,
    batchReviewStatus,
    submittingBatchReview,
    updatingReview,
    setBatchReviewStatus,
    handleExportReport,
    handleExportDocx,
    handleBatchExport,
    handleCopyReportText,
    handleReviewStatusChange,
    handleReviewNoteSave,
    handleBatchReviewStatusChange,
  } = useReportActions({
    selected,
    activeView,
    selectedReportIds,
    reviewNoteDraft,
    setSelected,
    setReports,
    setSelectedReportIds,
    setDetailError,
    setListError,
    setTaskMessage,
    loadReviewEvents,
  });
  const {
    isReportListBusy,
    reportListBusyMessage,
  } = getReportListBusyState({
    submittingAIReportId,
    submittingBatchReview,
    exportingBatchFormat,
  });
  const totalPages = Math.max(1, Math.ceil(totalReports / PAGE_SIZE));

  return (
    <AppShell>
      <div className="page-header">
        <h1>研究报告</h1>
        <p>筛选待复核报告，阅读 AI 翻译与评论稿，并导出可交付成果。</p>
      </div>

      <section className="report-workbench-intro" aria-label="报告处理流程">
        <div>
          <strong>1. 筛选</strong>
          <span>优先处理“待老师复核”和“可直接导出”。</span>
        </div>
        <div>
          <strong>2. 阅读</strong>
          <span>先看主要观点和深层研判，再核对全文翻译或原文。</span>
        </div>
        <div>
          <strong>3. 交付</strong>
          <span>复核通过后复制评论稿，或导出 Word / Markdown。</span>
        </div>
      </section>

      {loadingList && <p>正在加载报告列表……</p>}
      {listError && <p className="message-error">{listError}</p>}

      <div className="split-layout">
        <ReportListPanel
          reports={reports}
          sourcesById={sourceById}
          thinkTanksById={thinkTankById}
          selectedReportIds={selectedReportIds}
          activeReportId={selected?.id ?? null}
          canRetryAI={canRetryAI}
          loadingList={loadingList}
          isReportListBusy={isReportListBusy}
          reportListBusyMessage={reportListBusyMessage}
          submittingAIReportId={submittingAIReportId}
          searchDraft={searchDraft}
          keywordFilter={keywordFilter}
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
          visibleSelectedReportCount={visibleSelectedReportCount}
          allVisibleSelected={allVisibleSelected}
          batchReviewStatus={batchReviewStatus}
          submittingBatchReview={submittingBatchReview}
          exportingBatchFormat={exportingBatchFormat}
          onSearchDraftChange={setSearchDraft}
          onSearchSubmit={handleSearchSubmit}
          onSearchClear={handleSearchClear}
          onResetFilters={handleResetFilters}
          onReviewStatusChange={handleReviewStatusFilterChange}
          onAIStatusChange={handleAIStatusFilterChange}
          onContentKindChange={handleContentKindFilterChange}
          onDeliverableStatusChange={handleDeliverableStatusFilterChange}
          onThinkTankChange={handleThinkTankFilterChange}
          onSourceChange={handleSourceFilterChange}
          onWorkflowShortcut={handleWorkflowShortcut}
          onPreviousPage={() =>
            setPage((current) => Math.max(1, current - 1))
          }
          onNextPage={() =>
            setPage((current) => Math.min(totalPages, current + 1))
          }
          onToggleAllVisible={toggleAllVisibleReports}
          onClearSelection={clearReportSelection}
          onBatchReviewStatusChange={setBatchReviewStatus}
          onApplyBatchReview={handleBatchReviewStatusChange}
          onBatchExport={handleBatchExport}
          onSelectReport={handleSelect}
          onToggleReportSelection={toggleReportSelection}
          onRetryAI={submitRetryAI}
        />

        <ReportDetailPanel
          selected={selected}
          selectedDocumentType={selectedDocumentType}
          selectedSource={selectedSource ?? null}
          selectedThinkTank={selectedThinkTank ?? null}
          loadingDetail={loadingDetail}
          detailError={detailError}
          taskMessage={taskMessage}
          activeView={activeView}
          copyingTarget={copyingTarget}
          exportingReport={exportingReport}
          exportingDocx={exportingDocx}
          canFetchContent={canFetchContent}
          canRetryAI={canRetryAI}
          submittingFetch={submittingFetch}
          submittingAIReportId={submittingAIReportId}
          aiActionLabel={aiActionLabel}
          updatingReview={updatingReview}
          reviewNoteDraft={reviewNoteDraft}
          highlightReviewSection={highlightReviewSection}
          reviewSectionRef={reviewSectionRef}
          adminDetailsSummary={adminDetailsSummary}
          reviewHistorySummary={reviewHistorySummary}
          aiProgressSummary={aiProgressSummary}
          loadingReviewEvents={loadingReviewEvents}
          reviewEventsError={reviewEventsError}
          reviewEvents={reviewEvents}
          loadingProgress={loadingProgress}
          progressError={progressError}
          aiProgress={aiProgress}
          openReviewDetails={openReviewDetails}
          onViewSelect={setActiveView}
          onCopyCommentary={() => handleCopyReportText('commentary')}
          onCopyTranslation={() => handleCopyReportText('translation')}
          onCopyCurrent={() => handleCopyReportText('current')}
          onExportMarkdown={handleExportReport}
          onExportDocx={handleExportDocx}
          onReviewStatusChange={handleReviewStatusChange}
          onReviewNoteChange={setReviewNoteDraft}
          onReviewNoteSave={handleReviewNoteSave}
          onFetchContent={handleFetchContent}
          onRetryAI={handleRetryAI}
        />
      </div>
    </AppShell>
  );
}

export default function ReportsPage() {
  return (
    <Suspense
      fallback={
        <AppShell>
          <p>正在加载报告列表……</p>
        </AppShell>
      }
    >
      <ReportsPageContent />
    </Suspense>
  );
}
