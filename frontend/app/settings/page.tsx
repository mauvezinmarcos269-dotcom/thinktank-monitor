'use client';

import { type FormEvent, useEffect, useMemo, useState } from 'react';

import { AppShell } from '@/components/app-shell';
import {
  createThinkTankSource,
  downloadCrawlCandidatesCsv,
  fetchCrawlCandidateStatistics,
  fetchCrawlCandidates,
  fetchInstitutionStats,
  fetchMissingSourceThinkTanks,
  fetchSourceHealth,
  fetchThinkTanks,
  triggerSourceCrawl,
  type CrawlCandidate,
  type CrawlCandidateStatistics,
  type InstitutionStats,
  type SourceCreateInput,
  type SourceHealth,
  type SourceHealthSummary,
  type ThinkTank,
} from '@/lib/institution';
import { CandidateDetail, type CandidateFilters } from './candidate-detail';
import { MissingSourcesPanel } from './missing-sources-panel';
import { ReviewQueuePanel } from './review-queue-panel';
import {
  candidatePageSize,
  candidateReasonOptions,
  crawlableSourceTypes,
  crawlRunBadgeClasses,
  documentPolicyLabels,
  formatDateTime,
  formatDuration,
  getLatestRun,
  getSaveRate,
  getSourceHealthFilterCounts,
  getSourceReviewReason,
  healthBadgeClasses,
  healthLabels,
  matchesSourceHealthFilter,
  rolloutStageBadgeClasses,
  rolloutStageLabels,
  sortSourceHealth,
  sourceHealthFilterOptions,
  type SourceHealthFilter,
  sourceTypeOptions,
} from './settings-page-utils';
import { SourceCreateForm } from './source-create-form';
import { SourceHealthList } from './source-health-list';
import { SettingsOverviewPanels } from './settings-overview-panels';
import { SettingsWorkbenchIntro } from './settings-workbench-intro';

export default function SettingsPage() {
  const [stats, setStats] = useState<InstitutionStats | null>(null);
  const [thinkTanks, setThinkTanks] = useState<ThinkTank[]>([]);
  const [sourceHealth, setSourceHealth] = useState<SourceHealth[]>([]);
  const [sourceHealthFilter, setSourceHealthFilter] =
    useState<SourceHealthFilter>('all');
  const [sourceHealthSearch, setSourceHealthSearch] = useState('');
  const [sourceHealthSummary, setSourceHealthSummary] =
    useState<SourceHealthSummary | null>(null);
  const [missingSources, setMissingSources] = useState<ThinkTank[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [selectedThinkTankId, setSelectedThinkTankId] = useState('');
  const [sourceType, setSourceType] =
    useState<SourceCreateInput['source_type']>('rss');
  const [sourceUrl, setSourceUrl] = useState('');
  const [crawlFrequencyMinutes, setCrawlFrequencyMinutes] = useState(1440);
  const [crawlAfterCreate, setCrawlAfterCreate] = useState(true);
  const [submittingSource, setSubmittingSource] = useState(false);
  const [crawlingSourceId, setCrawlingSourceId] = useState<number | null>(null);
  const [expandedRunId, setExpandedRunId] = useState<number | null>(null);
  const [candidateLoadingRunId, setCandidateLoadingRunId] = useState<
    number | null
  >(null);
  const [candidateExportingRunId, setCandidateExportingRunId] = useState<
    number | null
  >(null);
  const [candidatesByRunId, setCandidatesByRunId] = useState<
    Record<number, CrawlCandidate[]>
  >({});
  const [candidateTotalByRunId, setCandidateTotalByRunId] = useState<
    Record<number, number>
  >({});
  const [candidateStatisticsByRunId, setCandidateStatisticsByRunId] = useState<
    Record<number, CrawlCandidateStatistics>
  >({});
  const [candidateFiltersByRunId, setCandidateFiltersByRunId] = useState<
    Record<number, CandidateFilters>
  >({});

  const thinkTankNameById = useMemo(() => {
    return new Map(
      thinkTanks.map((thinkTank) => [
        thinkTank.id,
        `${thinkTank.name} / ${thinkTank.country}`,
      ])
    );
  }, [thinkTanks]);

  const reviewQueue = useMemo(() => {
    return sourceHealth
      .map((source) => ({
        source,
        reason: getSourceReviewReason(source),
      }))
      .filter(
        (item): item is { source: SourceHealth; reason: string } =>
          item.reason !== null
      )
      .slice(0, 8);
  }, [sourceHealth]);

  const sourceHealthFilterCounts = useMemo(
    () => getSourceHealthFilterCounts(sourceHealth),
    [sourceHealth]
  );

  const filteredSourceHealth = useMemo(
    () => {
      const keyword = sourceHealthSearch.trim().toLowerCase();

      return sourceHealth.filter((source) => {
        if (!matchesSourceHealthFilter(source, sourceHealthFilter)) {
          return false;
        }

        if (!keyword) {
          return true;
        }

        return [
          source.think_tank_name,
          source.think_tank_key,
          source.think_tank_country,
          source.url,
          source.health_reason,
          source.diagnosis_label,
          source.diagnosis_advice,
          source.rollout_advice,
        ]
          .join(' ')
          .toLowerCase()
          .includes(keyword);
      });
    },
    [sourceHealth, sourceHealthFilter, sourceHealthSearch]
  );
  const activeSourceHealthFilterLabel =
    sourceHealthFilterOptions.find(
      (option) => option.value === sourceHealthFilter
    )?.label ?? '全部';

  async function loadSettings() {
    setLoading(true);
    setErrorMessage(null);

    try {
      const [statsData, thinkTanksData, missingSourceData, sourceHealthData] =
        await Promise.all([
          fetchInstitutionStats(),
          fetchThinkTanks(),
          fetchMissingSourceThinkTanks(),
          fetchSourceHealth(),
        ]);

      setStats(statsData);
      setThinkTanks(thinkTanksData);
      setMissingSources(missingSourceData);
      setSourceHealth(sortSourceHealth(sourceHealthData.items));
      setSourceHealthSummary(sourceHealthData.summary);

      setSelectedThinkTankId((current) => {
        if (current) {
          return current;
        }

        const firstMissingSource = missingSourceData[0];
        const firstThinkTank = thinkTanksData[0];
        return String(firstMissingSource?.id ?? firstThinkTank?.id ?? '');
      });
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '系统设置加载失败。'
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSettings();
  }, []);

  async function handleCreateSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    const thinkTankId = Number(selectedThinkTankId);

    if (!thinkTankId) {
      setErrorMessage('请选择机构。');
      return;
    }

    if (!sourceUrl.trim()) {
      setErrorMessage('请输入来源 URL。');
      return;
    }

    setSubmittingSource(true);

    try {
      const createdSource = await createThinkTankSource(thinkTankId, {
        source_type: sourceType,
        url: sourceUrl.trim(),
        crawl_frequency_minutes: crawlFrequencyMinutes,
        is_active: true,
      });

      if (crawlAfterCreate && crawlableSourceTypes.has(sourceType)) {
        const response = await triggerSourceCrawl(createdSource.id);
        setSuccessMessage(`${response.message} 任务 ID：${response.task_id}`);
      } else if (crawlAfterCreate) {
        setSuccessMessage('来源已添加；该类型暂不支持立即试抓。');
      } else {
        setSuccessMessage('来源已添加。');
      }

      setSourceUrl('');
      await loadSettings();
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '来源添加失败。'
      );
    } finally {
      setSubmittingSource(false);
    }
  }

  async function handleTriggerCrawl(sourceId: number) {
    setErrorMessage(null);
    setSuccessMessage(null);
    setCrawlingSourceId(sourceId);

    try {
      const response = await triggerSourceCrawl(sourceId);
      setSuccessMessage(`${response.message} 任务 ID：${response.task_id}`);
      await loadSettings();
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '抓取任务提交失败。'
      );
    } finally {
      setCrawlingSourceId(null);
    }
  }

  async function handleToggleCandidates(crawlRunId: number) {
    if (expandedRunId === crawlRunId) {
      setExpandedRunId(null);
      return;
    }

    setExpandedRunId(crawlRunId);

    if (candidatesByRunId[crawlRunId]) {
      return;
    }

    setCandidateLoadingRunId(crawlRunId);
    setErrorMessage(null);

    try {
      const filters = candidateFiltersByRunId[crawlRunId] ?? {
        status: '',
        reason: '',
      };
      const [response, statistics] = await Promise.all([
        fetchCrawlCandidates({
          crawlRunId,
          skip: 0,
          limit: candidatePageSize,
          status: filters.status,
          skipReasonLabel: filters.reason,
        }),
        fetchCrawlCandidateStatistics(crawlRunId),
      ]);
      setCandidatesByRunId((current) => ({
        ...current,
        [crawlRunId]: response.items,
      }));
      setCandidateTotalByRunId((current) => ({
        ...current,
        [crawlRunId]: response.total,
      }));
      setCandidateStatisticsByRunId((current) => ({
        ...current,
        [crawlRunId]: statistics,
      }));
      setCandidateFiltersByRunId((current) => ({
        ...current,
        [crawlRunId]: current[crawlRunId] ?? { status: '', reason: '' },
      }));
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '候选明细加载失败。'
      );
    } finally {
      setCandidateLoadingRunId(null);
    }
  }

  async function handleLoadMoreCandidates(crawlRunId: number) {
    const currentCandidates = candidatesByRunId[crawlRunId] ?? [];
    const filters = candidateFiltersByRunId[crawlRunId] ?? {
      status: '',
      reason: '',
    };

    setCandidateLoadingRunId(crawlRunId);
    setErrorMessage(null);

    try {
      const response = await fetchCrawlCandidates({
        crawlRunId,
        skip: currentCandidates.length,
        limit: candidatePageSize,
        status: filters.status,
        skipReasonLabel: filters.reason,
      });
      setCandidatesByRunId((current) => ({
        ...current,
        [crawlRunId]: [...(current[crawlRunId] ?? []), ...response.items],
      }));
      setCandidateTotalByRunId((current) => ({
        ...current,
        [crawlRunId]: response.total,
      }));
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '更多候选明细加载失败。'
      );
    } finally {
      setCandidateLoadingRunId(null);
    }
  }

  async function updateCandidateFilter(
    crawlRunId: number,
    field: keyof CandidateFilters,
    value: string
  ) {
    const previous = candidateFiltersByRunId[crawlRunId] ?? {
      status: '',
      reason: '',
    };
    const next = { ...previous, [field]: value };

    if (field === 'status' && value !== 'skipped') {
      next.reason = '';
    }

    setCandidateFiltersByRunId((current) => {
      return {
        ...current,
        [crawlRunId]: next,
      };
    });

    setCandidateLoadingRunId(crawlRunId);
    setErrorMessage(null);

    try {
      const response = await fetchCrawlCandidates({
        crawlRunId,
        skip: 0,
        limit: candidatePageSize,
        status: next.status,
        skipReasonLabel: next.reason,
      });
      setCandidatesByRunId((current) => ({
        ...current,
        [crawlRunId]: response.items,
      }));
      setCandidateTotalByRunId((current) => ({
        ...current,
        [crawlRunId]: response.total,
      }));
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '候选明细筛选失败。'
      );
    } finally {
      setCandidateLoadingRunId(null);
    }
  }

  async function handleExportCandidates(crawlRunId: number) {
    const filters = candidateFiltersByRunId[crawlRunId] ?? {
      status: '',
      reason: '',
    };

    setCandidateExportingRunId(crawlRunId);
    setErrorMessage(null);

    try {
      const blob = await downloadCrawlCandidatesCsv({
        crawlRunId,
        status: filters.status,
        skipReasonLabel: filters.reason,
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      const suffix = filters.status || filters.reason ? '-filtered' : '';

      link.href = url;
      link.download = `crawl-candidates-run-${crawlRunId}${suffix}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '候选明细导出失败。'
      );
    } finally {
      setCandidateExportingRunId(null);
    }
  }

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
        onFilterChange={updateCandidateFilter}
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

      <SettingsOverviewPanels
        stats={stats}
        sourceHealthSummary={sourceHealthSummary}
      />

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

      <section className="panel">
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
              className={
                sourceHealthFilter === option.value
                  ? 'source-health-filter-active'
                  : undefined
              }
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
            {sourceHealthFilter !== 'all'
              ? `，筛选：${activeSourceHealthFilterLabel}`
              : ''}
            {sourceHealthSearch.trim()
              ? `，搜索：${sourceHealthSearch.trim()}`
              : ''}
          </span>
          {sourceHealthFilter !== 'all' || sourceHealthSearch.trim() ? (
            <button
              type="button"
              onClick={() => {
                setSourceHealthFilter('all');
                setSourceHealthSearch('');
              }}
            >
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
