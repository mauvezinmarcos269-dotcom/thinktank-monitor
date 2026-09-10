'use client';

import { Fragment, type FormEvent, useEffect, useMemo, useState } from 'react';

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

const crawlRunLabels: Record<string, string> = {
  pending: '等待中',
  running: '抓取中',
  success: '成功',
  failed: '失败',
};

const crawlRunBadgeClasses: Record<string, string> = {
  pending: 'badge',
  running: 'badge badge-warning',
  success: 'badge badge-success',
  failed: 'badge badge-danger',
};

const candidateLabels: Record<string, string> = {
  discovered: '已发现',
  skipped: '已跳过',
  saved: '已入库',
};

const candidateBadgeClasses: Record<string, string> = {
  discovered: 'badge',
  skipped: 'badge badge-warning',
  saved: 'badge badge-success',
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

type CandidateFilters = {
  status: string;
  reason: string;
};

function formatDateTime(value: string | null): string {
  if (!value) {
    return '暂无';
  }

  return new Date(value).toLocaleString('zh-CN', {
    hour12: false,
  });
}

function buildLoadedCandidateReasonOptions(candidates: CrawlCandidate[]): string[] {
  const reasons = new Set<string>();

  candidates.forEach((candidate) => {
    if (candidate.skip_reason_label) {
      reasons.add(candidate.skip_reason_label);
    }
  });

  return [...reasons].sort((left, right) => left.localeCompare(right, 'zh-CN'));
}

function filterCandidates(
  candidates: CrawlCandidate[],
  filters: CandidateFilters
): CrawlCandidate[] {
  return candidates.filter((candidate) => {
    if (filters.status && candidate.status !== filters.status) {
      return false;
    }

    if (filters.reason && candidate.skip_reason_label !== filters.reason) {
      return false;
    }

    return true;
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
    const loadedReasonOptions = buildLoadedCandidateReasonOptions(candidates);
    const filteredCandidates = filterCandidates(candidates, filters);

    if (candidateLoadingRunId === crawlRunId) {
      return <p className="muted">正在加载候选明细……</p>;
    }

    if (candidates.length === 0) {
      return (
        <p className="muted">这次抓取暂无候选明细。历史运行不会自动回填。</p>
      );
    }

    return (
      <>
        <div className="candidate-summary">
          <span className="badge">全部 {statistics?.total ?? totalCandidates}</span>
          {statistics?.by_status.map((item) => (
            <span
              key={item.code ?? item.label}
              className={candidateBadgeClasses[item.code ?? ''] ?? 'badge'}
            >
              {item.label} {item.count}
            </span>
          ))}
        </div>

        {statistics?.by_skip_reason.length ? (
          <div className="candidate-reason-summary">
            {statistics.by_skip_reason.map((item) => (
              <span key={item.code ?? item.label} className="badge">
                {item.label} {item.count}
              </span>
            ))}
          </div>
        ) : loadedReasonOptions.length > 0 ? (
          <div className="candidate-reason-summary">
            {loadedReasonOptions.map((reason) => (
              <span key={reason} className="badge">
                {reason}{' '}
                {
                  candidates.filter(
                    (candidate) => candidate.skip_reason_label === reason
                  ).length
                }
              </span>
            ))}
          </div>
        ) : null}

        <div className="candidate-filters">
          <label>
            状态
            <select
              value={filters.status}
              onChange={(event) =>
                updateCandidateFilter(crawlRunId, 'status', event.target.value)
              }
            >
              <option value="">全部状态</option>
              {Object.entries(candidateLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>

          <label>
            跳过原因
            <select
              value={filters.reason}
              onChange={(event) =>
                updateCandidateFilter(crawlRunId, 'reason', event.target.value)
              }
              disabled={filters.status !== '' && filters.status !== 'skipped'}
            >
              <option value="">全部原因</option>
              {candidateReasonOptions.map((reason) => (
                <option key={reason} value={reason}>
                  {reason}
                </option>
              ))}
            </select>
          </label>

          <span className="muted">
            当前筛选共 {totalCandidates} 条；已加载 {candidates.length} 条；当前显示{' '}
            {filteredCandidates.length} 条
          </span>

          <button
            type="button"
            onClick={() => handleExportCandidates(crawlRunId)}
            disabled={candidateExportingRunId === crawlRunId}
          >
            {candidateExportingRunId === crawlRunId
              ? '导出中……'
              : '导出 CSV'}
          </button>
        </div>

        {filteredCandidates.length === 0 ? (
          <p className="muted">当前筛选条件下暂无候选。</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>标题</th>
                <th>状态</th>
                <th>跳过原因</th>
                <th>页数</th>
                <th>涉华</th>
                <th>链接</th>
                <th>说明</th>
              </tr>
            </thead>
            <tbody>
              {filteredCandidates.map((candidate) => (
                <tr key={candidate.id}>
                  <td className="candidate-title">
                    {candidate.title ?? '无标题'}
                  </td>
                  <td>
                    <span
                      className={
                        candidateBadgeClasses[candidate.status] ?? 'badge'
                      }
                    >
                      {candidateLabels[candidate.status] ?? candidate.status}
                    </span>
                  </td>
                  <td>{candidate.skip_reason_label ?? '无'}</td>
                  <td>{candidate.page_count ?? '暂无'}</td>
                  <td>
                    {candidate.is_china_related === null
                      ? '未判断'
                      : candidate.is_china_related
                        ? '是'
                        : '否'}
                  </td>
                  <td>
                    <a href={candidate.url} target="_blank" rel="noreferrer">
                      打开
                    </a>
                  </td>
                  <td className="candidate-note">
                    {candidate.error ?? candidate.relevance_reason ?? '无'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {candidates.length < totalCandidates ? (
          <div className="candidate-load-more">
            <button
              type="button"
              onClick={() => handleLoadMoreCandidates(crawlRunId)}
              disabled={candidateLoadingRunId === crawlRunId}
            >
              {candidateLoadingRunId === crawlRunId
                ? '加载中……'
                : `加载更多（剩余 ${totalCandidates - candidates.length} 条）`}
            </button>
          </div>
        ) : null}
      </>
    );
  }

  return (
    <AppShell>
      <div className="page-header">
        <h1>系统设置</h1>
        <p>维护智库来源、抓取频率和手动采集任务。</p>
      </div>

      {loading && <p>正在加载系统配置……</p>}
      {errorMessage && <p className="message-error">{errorMessage}</p>}
      {successMessage && <p className="message-success">{successMessage}</p>}

      {stats && (
        <section className="panel">
          <h2>来源配置概览</h2>

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
          <h2>来源健康概览</h2>

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
        <h2>添加来源</h2>

        <form className="form-grid" onSubmit={handleCreateSource}>
          <div className="form-field">
            <label htmlFor="think-tank-id">机构</label>
            <select
              id="think-tank-id"
              value={selectedThinkTankId}
              onChange={(event) => setSelectedThinkTankId(event.target.value)}
              disabled={submittingSource}
              required
            >
              <option value="">请选择机构</option>
              {thinkTanks.map((thinkTank) => (
                <option key={thinkTank.id} value={thinkTank.id}>
                  {thinkTank.name} / {thinkTank.country}
                </option>
              ))}
            </select>
          </div>

          <div className="form-field">
            <label htmlFor="source-type">来源类型</label>
            <select
              id="source-type"
              value={sourceType}
              onChange={(event) =>
                setSourceType(
                  event.target.value as SourceCreateInput['source_type']
                )
              }
              disabled={submittingSource}
            >
              {sourceTypeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="form-field">
            <label htmlFor="source-url">URL</label>
            <input
              id="source-url"
              type="url"
              value={sourceUrl}
              onChange={(event) => setSourceUrl(event.target.value)}
              placeholder="https://example.org/feed/"
              disabled={submittingSource}
              required
            />
          </div>

          <div className="form-field">
            <label htmlFor="crawl-frequency">抓取频率（分钟）</label>
            <input
              id="crawl-frequency"
              type="number"
              min={5}
              max={43200}
              value={crawlFrequencyMinutes}
              onChange={(event) =>
                setCrawlFrequencyMinutes(Number(event.target.value))
              }
              disabled={submittingSource}
            />
          </div>

          <div className="form-field">
            <label htmlFor="crawl-after-create">
              <input
                id="crawl-after-create"
                type="checkbox"
                checked={crawlAfterCreate}
                onChange={(event) =>
                  setCrawlAfterCreate(event.target.checked)
                }
                disabled={submittingSource}
              />
              添加后立即试抓
            </label>
          </div>

          <button type="submit" disabled={submittingSource}>
            {submittingSource ? '正在提交……' : '添加来源'}
          </button>
        </form>
      </section>

      <section className="panel">
        <h2>待配置来源机构</h2>

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
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel">
        <h2>来源健康与手动重试</h2>

        <div className="toolbar">
          <button type="button" onClick={loadSettings} disabled={loading}>
            {loading ? '刷新中……' : '刷新状态'}
          </button>
        </div>

        {sourceHealth.length === 0 && !loading ? (
          <p>暂无来源。</p>
        ) : (
          <ul className="source-health-list">
            {sourceHealth.map((source) => (
              <li key={source.id} className="source-health-item">
                <div className="source-health-main">
                  <div>
                    <strong>{source.think_tank_name}</strong>
                    <span className="muted"> / {source.think_tank_country}</span>
                  </div>
                  <a href={source.url} target="_blank" rel="noreferrer">
                    {source.url}
                  </a>
                  <p>{source.health_reason}</p>
                </div>

                <dl className="source-health-meta">
                  <div>
                    <dt>健康状态</dt>
                    <dd>
                      <span className={healthBadgeClasses[source.health_status]}>
                        {healthLabels[source.health_status]}
                      </span>
                    </dd>
                  </div>
                  <div>
                    <dt>来源类型</dt>
                    <dd>{source.source_type}</dd>
                  </div>
                  <div>
                    <dt>最近抓取</dt>
                    <dd>{formatDateTime(source.last_crawled_at)}</dd>
                  </div>
                  <div>
                    <dt>最近入库报告</dt>
                    <dd>{formatDateTime(source.latest_report_created_at)}</dd>
                  </div>
                  <div>
                    <dt>报告数</dt>
                    <dd>{source.report_count}</dd>
                  </div>
                  <div>
                    <dt>频率</dt>
                    <dd>{source.crawl_frequency_minutes} 分钟</dd>
                  </div>
                  <div>
                    <dt>问题类型</dt>
                    <dd>
                      <span className="badge">{source.diagnosis_label}</span>
                    </dd>
                  </div>
                </dl>

                <p className="source-advice">{source.diagnosis_advice}</p>

                {source.last_error ? (
                  <p className="source-error">{source.last_error}</p>
                ) : null}

                <div className="crawl-run-history">
                  <h3>最近抓取记录</h3>
                  {source.recent_crawl_runs.length === 0 ? (
                    <p className="muted">暂无抓取运行记录。</p>
                  ) : (
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>开始时间</th>
                            <th>状态</th>
                            <th>发现</th>
                            <th>入库</th>
                            <th>耗时</th>
                            <th>质量/错误摘要</th>
                            <th>候选</th>
                          </tr>
                        </thead>
                        <tbody>
                          {source.recent_crawl_runs.map((run) => (
                            <Fragment key={run.id}>
                              <tr>
                                <td>{formatDateTime(run.started_at)}</td>
                                <td>
                                  <span
                                    className={
                                      crawlRunBadgeClasses[run.status] ??
                                      'badge'
                                    }
                                  >
                                    {crawlRunLabels[run.status] ?? run.status}
                                  </span>
                                </td>
                                <td>{run.found_count}</td>
                                <td>{run.saved_count}</td>
                                <td>{formatDuration(run.duration_seconds)}</td>
                                <td className="crawl-run-error">
                                  {run.error ?? '无'}
                                </td>
                                <td>
                                  <button
                                    type="button"
                                    onClick={() => handleToggleCandidates(run.id)}
                                    disabled={candidateLoadingRunId === run.id}
                                  >
                                    {candidateLoadingRunId === run.id
                                      ? '加载中……'
                                      : expandedRunId === run.id
                                        ? '收起'
                                        : '查看候选'}
                                  </button>
                                </td>
                              </tr>
                              {expandedRunId === run.id ? (
                                <tr>
                                  <td colSpan={7}>
                                    <div className="candidate-detail">
                                      {renderCandidateDetail(run.id)}
                                    </div>
                                  </td>
                                </tr>
                              ) : null}
                            </Fragment>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => handleTriggerCrawl(source.id)}
                  disabled={
                    crawlingSourceId === source.id ||
                    !source.is_active ||
                    !crawlableSourceTypes.has(
                      source.source_type as SourceCreateInput['source_type']
                    )
                  }
                >
                  {crawlingSourceId === source.id ? '提交中……' : '手动重试'}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </AppShell>
  );
}
