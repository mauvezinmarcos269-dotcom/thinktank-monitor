'use client';

import { Suspense, useEffect, useRef } from 'react';
import { useSearchParams } from 'next/navigation';

import { AppShell } from '@/components/app-shell';
import { getCurrentUser } from '@/lib/auth';

import { CandidateDetail } from './candidate-detail';
import { MissingSourcesPanel } from './missing-sources-panel';
import { ReviewQueuePanel } from './review-queue-panel';
import {
  candidateReasonOptions,
  crawlableSourceTypes,
  crawlRunBadgeClasses,
  documentPolicyLabels,
  formatDateTime,
  formatDuration,
  getLatestRun,
  getSaveRate,
  getSourceReviewReason,
  healthBadgeClasses,
  healthLabels,
  isSourceHealthFilter,
  rolloutStageBadgeClasses,
  rolloutStageLabels,
  sourceHealthFilterOptions,
  sourceTypeOptions,
} from './settings-page-utils';
import { SettingsOverviewPanels } from './settings-overview-panels';
import { SettingsWorkbenchIntro } from './settings-workbench-intro';
import { SourceCreateForm } from './source-create-form';
import { SourceHealthList } from './source-health-list';
import { useCandidateDetails } from './use-candidate-details';
import { useSettingsData } from './use-settings-data';
import { useSourceCreateForm } from './use-source-create-form';
import { useSourceCrawlActions } from './use-source-crawl-actions';
import { useSourceHealthFilters } from './use-source-health-filters';

function SettingsPageContent() {
  const searchParams = useSearchParams();
  const sourceHealthSectionRef = useRef<HTMLElement | null>(null);
  const canAuthorize = getCurrentUser()?.role === 'admin';
  const sourceHealthFilterParam = searchParams.get('source_health');
  const sourceHealthSearchParam = searchParams.get('source_query') ?? searchParams.get('source_search') ?? '';
  const sourceIdParam = searchParams.get('source_id');
  const focusedSourceId = sourceIdParam && /^\d+$/.test(sourceIdParam) ? Number(sourceIdParam) : null;
  const shouldFocusSourceHealth =
    searchParams.get('focus') === 'source-health' ||
    sourceHealthFilterParam !== null ||
    sourceHealthSearchParam.trim() !== '' ||
    focusedSourceId !== null;
  const {
    stats,
    thinkTanks,
    sourceHealth,
    sourceHealthSummary,
    missingSources,
    loading,
    errorMessage,
    successMessage,
    setErrorMessage,
    setSuccessMessage,
    loadSettings,
  } = useSettingsData();

  const {
    sourceHealthFilter,
    setSourceHealthFilter,
    sourceHealthSearch,
    setSourceHealthSearch,
    reviewQueue,
    sourceHealthFilterCounts,
    filteredSourceHealth,
    activeSourceHealthFilterLabel,
    resetSourceHealthFilters,
  } = useSourceHealthFilters(sourceHealth);

  useEffect(() => {
    if (!shouldFocusSourceHealth) {
      return;
    }

    if (isSourceHealthFilter(sourceHealthFilterParam)) {
      setSourceHealthFilter(sourceHealthFilterParam);
    }

    if (sourceHealthSearchParam.trim()) {
      setSourceHealthSearch(sourceHealthSearchParam.trim());
    } else if (focusedSourceId !== null) {
      setSourceHealthSearch(String(focusedSourceId));
    }

    const scrollTimer = window.setTimeout(() => {
      window.requestAnimationFrame(() => {
        const focusedSource = focusedSourceId ? document.getElementById(`source-health-${focusedSourceId}`) : null;
        const target = focusedSource ?? sourceHealthSectionRef.current;

        if (!target) {
          return;
        }

        const top = target.getBoundingClientRect().top + window.scrollY - 16;
        window.scrollTo({ top: Math.max(top, 0), behavior: 'auto' });
      });
    }, 150);

    return () => window.clearTimeout(scrollTimer);
  }, [
    filteredSourceHealth.length,
    focusedSourceId,
    setSourceHealthFilter,
    setSourceHealthSearch,
    shouldFocusSourceHealth,
    sourceHealth.length,
    sourceHealthFilterParam,
    sourceHealthSearchParam,
  ]);

  const {
    selectedThinkTankId,
    sourceType,
    sourceUrl,
    crawlFrequencyMinutes,
    crawlAfterCreate,
    submittingSource,
    setSelectedThinkTankId,
    setSourceType,
    setSourceUrl,
    setCrawlFrequencyMinutes,
    setCrawlAfterCreate,
    handleCreateSource,
  } = useSourceCreateForm({
    thinkTanks,
    missingSources,
    loadSettings,
    setErrorMessage,
    setSuccessMessage,
  });

  const { crawlingSourceId, handleTriggerCrawl } = useSourceCrawlActions({
    loadSettings,
    setErrorMessage,
    setSuccessMessage,
  });

  const {
    expandedRunId,
    candidateLoadingRunId,
    candidateExportingRunId,
    candidatesByRunId,
    candidateTotalByRunId,
    candidateStatisticsByRunId,
    candidateFiltersByRunId,
    handleToggleCandidates,
    handleLoadMoreCandidates,
    updateCandidateFilter,
    applyCandidateFilters,
    handleExportCandidates,
  } = useCandidateDetails({
    setErrorMessage,
  });

  function renderCandidateDetail(crawlRunId: number) {
    const candidates = candidatesByRunId[crawlRunId] ?? [];
    const totalCandidates = candidateTotalByRunId[crawlRunId] ?? candidates.length;
    const statistics = candidateStatisticsByRunId[crawlRunId];
    const filters = candidateFiltersByRunId[crawlRunId] ?? {
      status: '',
      reason: '',
    };

    return (
      <CandidateDetail
        crawlRunId={crawlRunId}
        candidates={candidates}
        totalCandidates={totalCandidates}
        statistics={statistics}
        filters={filters}
        loading={candidateLoadingRunId === crawlRunId}
        exporting={candidateExportingRunId === crawlRunId}
        candidateReasonOptions={candidateReasonOptions}
        canAuthorize={canAuthorize}
        onFilterChange={updateCandidateFilter}
        onApplyFilters={applyCandidateFilters}
        onExportCandidates={handleExportCandidates}
        onLoadMoreCandidates={handleLoadMoreCandidates}
      />
    );
  }

  return (
    <AppShell>
      <div className="page-header">
        <h1>系统设置</h1>
        <p>维护监测来源、查看抓取质量，并处理需要人工确认的来源。</p>
      </div>

      <SettingsWorkbenchIntro />

      {loading && <p>正在加载系统配置……</p>}
      {errorMessage && <p className="message-error">{errorMessage}</p>}
      {successMessage && <p className="message-success">{successMessage}</p>}

      <SettingsOverviewPanels stats={stats} sourceHealthSummary={sourceHealthSummary} />

      <ReviewQueuePanel
        reviewQueue={reviewQueue}
        loading={loading}
        healthBadgeClasses={healthBadgeClasses}
        getLatestRun={getLatestRun}
        getSaveRate={getSaveRate}
        formatDateTime={formatDateTime}
      />

      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>添加来源</h2>
            <p>新增 RSS 或官网列表页后，可立即试抓并观察候选结果。</p>
          </div>
        </div>

        <SourceCreateForm
          thinkTanks={thinkTanks}
          selectedThinkTankId={selectedThinkTankId}
          sourceType={sourceType}
          sourceUrl={sourceUrl}
          crawlFrequencyMinutes={crawlFrequencyMinutes}
          crawlAfterCreate={crawlAfterCreate}
          submittingSource={submittingSource}
          sourceTypeOptions={sourceTypeOptions}
          onSubmit={handleCreateSource}
          onThinkTankChange={setSelectedThinkTankId}
          onSourceTypeChange={setSourceType}
          onSourceUrlChange={setSourceUrl}
          onCrawlFrequencyChange={setCrawlFrequencyMinutes}
          onCrawlAfterCreateChange={setCrawlAfterCreate}
        />
      </section>

      <MissingSourcesPanel missingSources={missingSources} loading={loading} />

      <section className="panel" id="source-health" ref={sourceHealthSectionRef}>
        <div className="section-heading">
          <div>
            <h2>来源健康与手动重试</h2>
            <p>查看每个来源的准入策略、最近抓取质量和候选报告明细。</p>
          </div>
          <button type="button" onClick={loadSettings} disabled={loading}>
            {loading ? '刷新中……' : '刷新状态'}
          </button>
        </div>

        <div className="source-health-filter-bar" aria-label="来源健康筛选">
          {sourceHealthFilterOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              className={sourceHealthFilter === option.value ? 'source-health-filter-active' : undefined}
              onClick={() => setSourceHealthFilter(option.value)}
              aria-pressed={sourceHealthFilter === option.value}
            >
              <span>{option.label}</span>
              <strong>{sourceHealthFilterCounts[option.value] ?? 0}</strong>
            </button>
          ))}
        </div>

        <label className="source-health-search">
          <span>搜索来源</span>
          <input
            type="search"
            value={sourceHealthSearch}
            onChange={(event) => setSourceHealthSearch(event.target.value)}
            placeholder="输入机构、国家、URL 或问题类型"
          />
        </label>

        <div className="source-health-filter-summary">
          <span>
            当前显示 {filteredSourceHealth.length} / {sourceHealth.length} 个来源
            {sourceHealthFilter !== 'all' ? `，筛选：${activeSourceHealthFilterLabel}` : ''}
            {sourceHealthSearch.trim() ? `，搜索：${sourceHealthSearch.trim()}` : ''}
          </span>
          {sourceHealthFilter !== 'all' || sourceHealthSearch.trim() ? (
            <button type="button" onClick={resetSourceHealthFilters}>
              清除筛选
            </button>
          ) : null}
        </div>

        <SourceHealthList
          sources={filteredSourceHealth}
          loading={loading}
          hasActiveFilter={sourceHealthFilter !== 'all'}
          crawlingSourceId={crawlingSourceId}
          expandedRunId={expandedRunId}
          candidateLoadingRunId={candidateLoadingRunId}
          crawlableSourceTypes={crawlableSourceTypes}
          healthLabels={healthLabels}
          healthBadgeClasses={healthBadgeClasses}
          rolloutStageLabels={rolloutStageLabels}
          rolloutStageBadgeClasses={rolloutStageBadgeClasses}
          documentPolicyLabels={documentPolicyLabels}
          crawlRunBadgeClasses={crawlRunBadgeClasses}
          focusedSourceId={focusedSourceId}
          onTriggerCrawl={handleTriggerCrawl}
          onToggleCandidates={handleToggleCandidates}
          renderCandidateDetail={renderCandidateDetail}
          getSourceReviewReason={getSourceReviewReason}
          getLatestRun={getLatestRun}
          getSaveRate={getSaveRate}
          formatDateTime={formatDateTime}
          formatDuration={formatDuration}
        />
      </section>
    </AppShell>
  );
}

export default function SettingsPage() {
  return (
    <Suspense
      fallback={
        <AppShell>
          <p>正在加载系统配置……</p>
        </AppShell>
      }
    >
      <SettingsPageContent />
    </Suspense>
  );
}
