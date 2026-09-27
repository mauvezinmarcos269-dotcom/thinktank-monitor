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
import { AIProgressPanel } from './ai-progress-panel';
import { ReportBatchActions } from './report-batch-actions';
import { ReportActionBar } from './report-action-bar';
import { ReportContentViewer } from './report-content-viewer';
import { ReportDetailHeader } from './report-detail-header';
import { ReportFilterBar } from './report-filter-bar';
import { ReportList } from './report-list';
import { ReportMetadataGrid } from './report-metadata-grid';
import { ReportOutcomeSummary } from './report-outcome-summary';
import {
  formatDateTime,
  getDocumentType,
  PAGE_SIZE,
} from './report-page-utils';
import { ReportReadingBrief } from './report-reading-brief';
import { ReviewHistoryPanel } from './review-history-panel';
import { useReportActions } from './use-report-actions';
import { useReportDetail } from './use-report-detail';
import { useReportFilters } from './use-report-filters';

function ReportsPageContent() {
  const searchParams = useSearchParams();
  const reviewSectionRef = useRef<HTMLDivElement | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [selectedReportIds, setSelectedReportIds] = useState<Set<number>>(
    () => new Set()
  );
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
  const visibleReportIds = reports.map((report) => report.id);
  const visibleSelectedReportCount = visibleReportIds.filter((reportId) =>
    selectedReportIds.has(reportId)
  ).length;
  const allVisibleSelected =
    visibleReportIds.length > 0 &&
    visibleSelectedReportCount === visibleReportIds.length;
  const reviewHistorySummary = useMemo(() => {
    if (loadingReviewEvents) {
      return '加载中';
    }

    if (reviewEventsError) {
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
  }, [loadingReviewEvents, reviewEvents, reviewEventsError]);
  const aiProgressSummary = useMemo(() => {
    if (loadingProgress) {
      return '加载中';
    }

    if (progressError) {
      return '读取失败';
    }

    if (!aiProgress) {
      return '暂无记录';
    }

    if (aiProgress.total_chunks === 0) {
      return '暂无分块';
    }

    const base = `${aiProgress.completed_chunks}/${aiProgress.total_chunks} 完成`;

    if (aiProgress.failed_chunks > 0) {
      return `${base} · ${aiProgress.failed_chunks} 失败`;
    }

    if (aiProgress.running_chunks > 0) {
      return `${base} · ${aiProgress.running_chunks} 运行中`;
    }

    return `${base} · 无失败`;
  }, [aiProgress, loadingProgress, progressError]);

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

  function toggleReportSelection(reportId: number) {
    setSelectedReportIds((current) => {
      const next = new Set(current);
      if (next.has(reportId)) {
        next.delete(reportId);
      } else {
        next.add(reportId);
      }
      return next;
    });
  }

  function toggleAllVisibleReports() {
    setSelectedReportIds((current) => {
      const next = new Set(current);
      if (allVisibleSelected) {
        visibleReportIds.forEach((reportId) => next.delete(reportId));
      } else {
        visibleReportIds.forEach((reportId) => next.add(reportId));
      }
      return next;
    });
  }

  function clearReportSelection() {
    setSelectedReportIds(new Set());
  }

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
            <article className="report-detail">
              <ReportDetailHeader
                report={selected}
                documentType={selectedDocumentType}
                source={selectedSource ?? null}
                thinkTank={selectedThinkTank ?? null}
              />

              <ReportReadingBrief
                report={selected}
                onViewSelect={setActiveView}
              />

              <ReportOutcomeSummary
                report={selected}
                activeView={activeView}
                copyingTarget={copyingTarget}
                exportingReport={exportingReport}
                exportingDocx={exportingDocx}
                onViewSelect={setActiveView}
                onCopyCommentary={() => handleCopyReportText('commentary')}
                onCopyTranslation={() => handleCopyReportText('translation')}
                onExportMarkdown={handleExportReport}
                onExportDocx={handleExportDocx}
              />

              {selected.crawl_error && (
                <p className="message-error">
                  抓取错误：{selected.crawl_error}
                </p>
              )}

              <ReportContentViewer
                report={selected}
                activeView={activeView}
                copyingTarget={copyingTarget}
                onActiveViewChange={setActiveView}
                onCopyCurrent={() => handleCopyReportText('current')}
              />

              <section className="secondary-detail-group">
                <details
                  className="secondary-details"
                  open={searchParams.get('focus') === 'review'}
                >
                  <summary>
                    <span>文档信息、复核与导出操作</span>
                    <small>{adminDetailsSummary}</small>
                  </summary>
                  <ReportMetadataGrid
                    report={selected}
                    documentType={selectedDocumentType}
                    source={selectedSource ?? null}
                    thinkTank={selectedThinkTank ?? null}
                    canReview={canRetryAI}
                    updatingReview={updatingReview}
                    reviewNoteDraft={reviewNoteDraft}
                    highlightReviewSection={highlightReviewSection}
                    reviewSectionRef={reviewSectionRef}
                    onReviewStatusChange={handleReviewStatusChange}
                    onReviewNoteChange={setReviewNoteDraft}
                    onReviewNoteSave={handleReviewNoteSave}
                  />

                  <ReportActionBar
                    report={selected}
                    canFetchContent={canFetchContent}
                    canRetryAI={canRetryAI}
                    submittingFetch={submittingFetch}
                    submittingAIReportId={submittingAIReportId}
                    exportingReport={exportingReport}
                    exportingDocx={exportingDocx}
                    copyingTarget={copyingTarget}
                    aiActionLabel={aiActionLabel}
                    onFetchContent={handleFetchContent}
                    onRetryAI={handleRetryAI}
                    onExportMarkdown={handleExportReport}
                    onExportDocx={handleExportDocx}
                    onCopyCommentary={() => handleCopyReportText('commentary')}
                    onCopyTranslation={() => handleCopyReportText('translation')}
                  />
                </details>

                <details className="secondary-details">
                  <summary>
                    <span>复核历史</span>
                    <small>{reviewHistorySummary}</small>
                  </summary>
                  <ReviewHistoryPanel
                    loading={loadingReviewEvents}
                    errorMessage={reviewEventsError}
                    events={reviewEvents}
                  />
                </details>

                <details className="secondary-details">
                  <summary>
                    <span>AI 分块进度</span>
                    <small>{aiProgressSummary}</small>
                  </summary>
                  <AIProgressPanel
                    loading={loadingProgress}
                    errorMessage={progressError}
                    progress={aiProgress}
                  />
                </details>
              </section>
            </article>
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
