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
import {
  crawlRunStatusLabels,
  priorityTierLabels,
  regionFocusLabels,
  type CrawlRunStatus,
} from '@/lib/status';
import { CandidateDetail, type CandidateFilters } from './candidate-detail';
import { SourceCreateForm } from './source-create-form';
import { SourceHealthList } from './source-health-list';

const sourceTypeOptions: Array<{
  value: SourceCreateInput['source_type'];
  label: string;
}> = [
  { value: 'rss', label: 'RSS' },
  { value: 'website', label: '官网/列表页' },
  { value: 'report_library', label: '报告库' },
  { value: 'topic_page', label: '专题页' },
];

const crawlableSourceTypes = new Set<SourceCreateInput['source_type']>([
  'rss',
  'website',
]);

const healthLabels: Record<SourceHealth['health_status'], string> = {
  healthy: '正常',
  warning: '需关注',
  failed: '失败',
  never: '未抓取',
  disabled: '停用',
};

const healthBadgeClasses: Record<SourceHealth['health_status'], string> = {
  healthy: 'badge badge-success',
  warning: 'badge badge-warning',
  failed: 'badge badge-danger',
  never: 'badge',
  disabled: 'badge',
};

const rolloutStageLabels: Record<string, string> = {
  pilot_crawl: '试运行',
  discovery_only: '仅发现',
  blocked: '阻塞',
  standard_review: '待复核',
};

const rolloutStageBadgeClasses: Record<string, string> = {
  pilot_crawl: 'badge badge-success',
  discovery_only: 'badge badge-warning',
  blocked: 'badge badge-danger',
  standard_review: 'badge',
};

const documentPolicyLabels: Record<string, string> = {
  pdf_20_page_required: '20页PDF',
  web_article_allowed: '网页长文',
  source_access_blocked: '入口不可达',
};

const crawlRunBadgeClasses: Record<CrawlRunStatus, string> = {
  pending: 'badge',
  running: 'badge badge-warning',
  success: 'badge badge-success',
  failed: 'badge badge-danger',
};

const candidateReasonOptions = [
  '无效 URL',
  '同一来源内重复',
  '已入库重复',
  'PDF 获取或页数/文本检查失败',
  '涉华判断失败',
  '非涉华',
  '并发重复入库',
];

const candidatePageSize = 50;

function formatDateTime(value: string | null): string {
  if (!value) {
    return '暂无';
  }

  return new Date(value).toLocaleString('zh-CN', {
    hour12: false,
  });
}

function formatDuration(value: number | null): string {
  if (value === null) {
    return '暂无';
  }

  if (value < 60) {
    return `${value} 秒`;
  }

  const minutes = Math.floor(value / 60);
  const seconds = value % 60;
  return seconds === 0 ? `${minutes} 分钟` : `${minutes} 分 ${seconds} 秒`;
}

function sortSourceHealth(items: SourceHealth[]): SourceHealth[] {
  const weight: Record<SourceHealth['health_status'], number> = {
    failed: 0,
    warning: 1,
    never: 2,
    healthy: 3,
    disabled: 4,
  };

  return [...items].sort((left, right) => {
    return weight[left.health_status] - weight[right.health_status];
  });
}

function getLatestRun(source: SourceHealth) {
  return source.recent_crawl_runs[0] ?? null;
}

function getSaveRate(run: SourceHealth['recent_crawl_runs'][number]): number {
  if (run.found_count <= 0) {
    return 0;
  }

  return Math.round((run.saved_count / run.found_count) * 100);
}

function getSourceReviewReason(source: SourceHealth): string | null {
  const latestRun = getLatestRun(source);

  if (source.rollout_stage === 'blocked') {
    return '来源入口阻塞';
  }

  if (source.rollout_stage === 'discovery_only') {
    return '仅发现待确认';
  }

  if (source.rollout_stage === 'standard_review') {
    return '待小样本复核';
  }

  if (!source.think_tank_is_verified) {
    return '机构信息待校对';
  }

  if (source.health_status === 'failed') {
    return '最近抓取失败';
  }

  if (source.health_status === 'never') {
    return '尚未试抓';
  }

  if (latestRun && latestRun.found_count > 0 && latestRun.saved_count === 0) {
    return '有候选但未入库';
  }

  if (latestRun && latestRun.status === 'running') {
    return '抓取仍在运行';
  }

  return null;
}

export default function SettingsPage() {
  const [stats, setStats] = useState<InstitutionStats | null>(null);
  const [thinkTanks, setThinkTanks] = useState<ThinkTank[]>([]);
  const [sourceHealth, setSourceHealth] = useState<SourceHealth[]>([]);
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

      <section className="settings-workbench-intro" aria-label="来源治理流程">
        <div>
          <strong>1. 覆盖重点机构</strong>
          <span>先补齐 P0/P1 智库来源，保证美国核心机构稳定监测。</span>
        </div>
        <div>
          <strong>2. 验收候选质量</strong>
          <span>查看候选报告、跳过原因和保存率，判断来源是否可放行。</span>
        </div>
        <div>
          <strong>3. 小批量试运行</strong>
          <span>只让通过复核的来源进入自动入库，异常来源先停留在人工确认。</span>
        </div>
      </section>

      {loading && <p>正在加载系统配置……</p>}
      {errorMessage && <p className="message-error">{errorMessage}</p>}
      {successMessage && <p className="message-success">{successMessage}</p>}

      {stats && (
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2>来源配置概览</h2>
              <p>用于判断监测网络是否覆盖了重点智库和机构。</p>
            </div>
          </div>

          <ul className="stats-grid">
            <li className="stat-card">
              机构总数
              <span className="stat-value">{stats.total_think_tanks}</span>
            </li>
            <li className="stat-card">
              重点机构
              <span className="stat-value">{stats.key_think_tanks}</span>
            </li>
            <li className="stat-card">
              来源总数
              <span className="stat-value">{stats.total_sources}</span>
            </li>
            <li className="stat-card">
              启用来源
              <span className="stat-value">{stats.active_sources}</span>
            </li>
            <li className="stat-card">
              待配置来源机构
              <span className="stat-value">{stats.missing_active_sources}</span>
            </li>
          </ul>
        </section>
      )}

      {sourceHealthSummary && (
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2>来源健康概览</h2>
              <p>优先处理失败、未抓取和需关注来源，减少漏报和噪声。</p>
            </div>
          </div>

          <ul className="stats-grid">
            <li className="stat-card">
              正常来源
              <span className="stat-value">
                {sourceHealthSummary.healthy_sources}
              </span>
            </li>
            <li className="stat-card">
              需关注
              <span className="stat-value">
                {sourceHealthSummary.warning_sources}
              </span>
            </li>
            <li className="stat-card">
              抓取失败
              <span className="stat-value">
                {sourceHealthSummary.failed_sources}
              </span>
            </li>
            <li className="stat-card">
              未抓取
              <span className="stat-value">
                {sourceHealthSummary.never_crawled_sources}
              </span>
            </li>
            <li className="stat-card">
              停用来源
              <span className="stat-value">
                {sourceHealthSummary.disabled_sources}
              </span>
            </li>
          </ul>
        </section>
      )}

      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>候选验收重点</h2>
            <p>这些来源需要先人工看候选质量，再决定是否进入自动入库。</p>
          </div>
        </div>

        {reviewQueue.length === 0 && !loading ? (
          <p>当前没有需要优先人工复核的来源。</p>
        ) : (
          <ul className="review-queue">
            {reviewQueue.map(({ source, reason }) => {
              const latestRun = getLatestRun(source);

              return (
                <li key={source.id}>
                  <div>
                    <strong>{source.think_tank_name}</strong>
                    <span className="muted">
                      {' '}
                      / {priorityTierLabels[source.think_tank_priority_tier]} /{' '}
                      {regionFocusLabels[source.think_tank_region_focus]}
                    </span>
                  </div>
                  <span className={healthBadgeClasses[source.health_status]}>
                    {reason}
                  </span>
                  <dl>
                    <div>
                      <dt>最近发现</dt>
                      <dd>{latestRun?.found_count ?? 0}</dd>
                    </div>
                    <div>
                      <dt>最近入库</dt>
                      <dd>{latestRun?.saved_count ?? 0}</dd>
                    </div>
                    <div>
                      <dt>保存率</dt>
                      <dd>
                        {latestRun ? `${getSaveRate(latestRun)}%` : '暂无'}
                      </dd>
                    </div>
                    <div>
                      <dt>最近抓取</dt>
                      <dd>{formatDateTime(source.last_crawled_at)}</dd>
                    </div>
                  </dl>
                </li>
              );
            })}
          </ul>
        )}
      </section>

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

      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>待配置来源机构</h2>
            <p>这些机构已在库中，但还没有启用的自动监测入口。</p>
          </div>
        </div>

        {missingSources.length === 0 && !loading ? (
          <p>所有启用机构都已有 active source。</p>
        ) : (
          <ul>
            {missingSources.map((thinkTank) => (
              <li key={thinkTank.id}>
                <strong>{thinkTank.name}</strong>
                {thinkTank.name_en ? ` / ${thinkTank.name_en}` : ''}
                {' - '}
                {thinkTank.country}
                {' - '}
                {priorityTierLabels[thinkTank.priority_tier]}
                {' - '}
                {thinkTank.is_verified ? '已校对' : '待校对'}
              </li>
            ))}
          </ul>
        )}
      </section>

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

        <SourceHealthList
          sources={sourceHealth}
          loading={loading}
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
