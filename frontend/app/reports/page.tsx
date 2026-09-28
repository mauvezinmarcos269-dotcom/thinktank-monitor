'use client';

import {
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useSearchParams } from 'next/navigation';

import { AppShell } from '@/components/app-shell';
import {
  getCurrentUser,
  type CurrentUser,
} from '@/lib/auth';
import {
  fetchSources,
  fetchThinkTanks,
  type Source,
  type ThinkTank,
} from '@/lib/institution';
import {
  fetchReports,
  type Report,
} from '@/lib/report';
import {
  reportAIStatusLabels,
  reportReviewStatusLabels,
} from '@/lib/status';
import { ReportBatchActions } from './report-batch-actions';
import { ReportDetailArticle } from './report-detail-article';
import { ReportFilterBar } from './report-filter-bar';
import { ReportList } from './report-list';
import {
  formatDateTime,
  getAIProgressSummary,
  getDocumentType,
  getReviewHistorySummary,
  PAGE_SIZE,
} from './report-page-utils';
import { useReportActions } from './use-report-actions';
import { useReportDetail } from './use-report-detail';
import { useReportFilters } from './use-report-filters';
import { useReportSelection } from './use-report-selection';

function ReportsPageContent() {
  const searchParams = useSearchParams();
  const reviewSectionRef = useRef<HTMLDivElement | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [thinkTanks, setThinkTanks] = useState<ThinkTank[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [totalReports, setTotalReports] = useState(0);

  const [listError, setListError] = useState<string | null>(null);
  const [taskMessage, setTaskMessage] = useState<string | null>(null);

  const [loadingList, setLoadingList] = useState(true);
  const [highlightReviewSection, setHighlightReviewSection] = useState(false);


  const [currentUser, setCurrentUser] =
    useState<CurrentUser | null>(null);
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

  const canFetchContent = currentUser?.role === 'admin';
  const canRetryAI = currentUser?.role === 'admin';
  const sourceOptions = thinkTankFilter
    ? sources.filter((source) => source.think_tank_id === thinkTankFilter)
    : sources;
  const sourceById = useMemo(
    () => new Map(sources.map((source) => [source.id, source])),
    [sources]
  );
  const thinkTankById = useMemo(
    () => new Map(thinkTanks.map((thinkTank) => [thinkTank.id, thinkTank])),
    [thinkTanks]
  );
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
  const isReportListBusy =
    submittingAIReportId !== null ||
    submittingBatchReview ||
    exportingBatchFormat !== null;
  const reportListBusyMessage = submittingAIReportId !== null
    ? 'AI 任务提交中，暂不可切换筛选。'
    : submittingBatchReview
      ? '批量复核处理中，暂不可切换筛选。'
      : exportingBatchFormat !== null
        ? '批量导出中，暂不可切换筛选。'
        : '';

  // 页面挂载后读取 sessionStorage 中的用户
  useEffect(() => {
    const user = getCurrentUser();
    setCurrentUser(user);
  }, []);

  useEffect(() => {
    Promise.all([
      fetchThinkTanks(),
      fetchSources(),
    ])
      .then(([nextThinkTanks, nextSources]) => {
        setThinkTanks(nextThinkTanks);
        setSources(nextSources);
      })
      .catch((err: Error) => setListError(err.message));
  }, []);

  useEffect(() => {
    if (!selected || searchParams.get('focus') !== 'review') {
      return;
    }

    const timer = window.setTimeout(() => {
      reviewSectionRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
      setHighlightReviewSection(true);
    }, 120);

    const clearTimer = window.setTimeout(() => {
      setHighlightReviewSection(false);
    }, 2600);

    return () => {
      window.clearTimeout(timer);
      window.clearTimeout(clearTimer);
    };
  }, [selected, searchParams]);


  // 加载报告列表
  useEffect(() => {
    setLoadingList(true);
    setListError(null);

    fetchReports({
      skip: (page - 1) * PAGE_SIZE,
      limit: PAGE_SIZE,
      reviewStatus: reviewStatusFilter,
      aiStatus: aiStatusFilter,
      contentKind: contentKindFilter,
      deliverableStatus: deliverableStatusFilter,
      keyword: keywordFilter,
      thinkTankId: thinkTankFilter,
      sourceId: sourceFilter,
    })
      .then((data) => {
        setReports(data.items);
        setTotalReports(data.total);
        setSelectedReportIds(new Set());

        const reportId = Number(searchParams.get('report_id'));

        if (reportId) {
          handleSelect(reportId);
        } else if (data.items.length > 0) {
          handleSelect(data.items[0].id);
        }
      })
      .catch((err: Error) => setListError(err.message))
      .finally(() => setLoadingList(false));
  }, [
    page,
    reviewStatusFilter,
    aiStatusFilter,
    contentKindFilter,
    deliverableStatusFilter,
    keywordFilter,
    thinkTankFilter,
    sourceFilter,
    searchParams,
    handleSelect,
    setSelectedReportIds,
  ]);

  const totalPages = Math.max(1, Math.ceil(totalReports / PAGE_SIZE));
  const selectedDocumentType = selected ? getDocumentType(selected) : null;
  const selectedSource = selected ? sourceById.get(selected.source_id) : null;
  const selectedThinkTank = selectedSource
    ? thinkTankById.get(selectedSource.think_tank_id)
    : null;
  const adminDetailsSummary =
    selected && selectedDocumentType
      ? [
          reportReviewStatusLabels[selected.review_status] ??
            selected.review_status,
          reportAIStatusLabels[selected.ai_status] ?? selected.ai_status,
          selectedDocumentType.label,
        ].join(' · ')
      : '暂无报告';
  const aiActionLabel =
    selected?.ai_status === 'skipped'
      ? '进入 AI 处理'
      : '重试 AI 处理';

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
              onSearchDraftChange={setSearchDraft}
              onSearchSubmit={handleSearchSubmit}
              onSearchClear={handleSearchClear}
              onResetFilters={handleResetFilters}
              onReviewStatusChange={handleReviewStatusFilterChange}
              onAIStatusChange={handleAIStatusFilterChange}
              onContentKindChange={handleContentKindFilterChange}
              onDeliverableStatusChange={
                handleDeliverableStatusFilterChange
              }
              onThinkTankChange={handleThinkTankFilterChange}
              onSourceChange={handleSourceFilterChange}
              onWorkflowShortcut={handleWorkflowShortcut}
              onPreviousPage={() =>
                setPage((current) => Math.max(1, current - 1))
              }
              onNextPage={() =>
                setPage((current) => Math.min(totalPages, current + 1))
              }
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
                onToggleAllVisible={toggleAllVisibleReports}
                onClearSelection={clearReportSelection}
                onBatchReviewStatusChange={setBatchReviewStatus}
                onApplyBatchReview={handleBatchReviewStatusChange}
                onBatchExport={handleBatchExport}
              />
            )}
          </div>

          <ReportList
            reports={reports}
            sourcesById={sourceById}
            thinkTanksById={thinkTankById}
            selectedReportIds={selectedReportIds}
            activeReportId={selected?.id ?? null}
            canRetryAI={canRetryAI}
            selectionDisabled={isReportListBusy}
            submittingAIReportId={submittingAIReportId}
            onSelectReport={handleSelect}
            onToggleReportSelection={toggleReportSelection}
            onRetryAI={submitRetryAI}
            onResetFilters={handleResetFilters}
          />
        </section>

        <section className="panel report-detail-panel">
          {loadingDetail && <p>正在加载报告详情……</p>}
          {detailError && (
            <p className="message-error">{detailError}</p>
          )}
          {taskMessage && (
            <p className="message-success">{taskMessage}</p>
          )}

          {selected && selectedDocumentType && !loadingDetail && (
            <ReportDetailArticle
              report={selected}
              documentType={selectedDocumentType}
              source={selectedSource ?? null}
              thinkTank={selectedThinkTank ?? null}
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
              openReviewDetails={searchParams.get('focus') === 'review'}
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
          )}

          {!selected && !loadingDetail && !detailError && (
            <div className="empty-state empty-state-large">
              <strong>请选择一篇报告</strong>
              <p>
                从左侧列表选择报告后，这里会显示全文翻译、主要观点和深层研判。
              </p>
            </div>
          )}
        </section>
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
