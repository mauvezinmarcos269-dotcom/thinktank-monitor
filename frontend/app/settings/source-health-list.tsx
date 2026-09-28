'use client';

import { Fragment, type ReactNode } from 'react';

import { type SourceCreateInput, type SourceHealth } from '@/lib/institution';
import { crawlRunStatusLabels, priorityTierLabels, regionFocusLabels } from '@/lib/status';

type SourceHealthListProps = {
  sources: SourceHealth[];
  loading: boolean;
  hasActiveFilter: boolean;
  crawlingSourceId: number | null;
  expandedRunId: number | null;
  candidateLoadingRunId: number | null;
  crawlableSourceTypes: Set<SourceCreateInput['source_type']>;
  healthLabels: Record<SourceHealth['health_status'], string>;
  healthBadgeClasses: Record<SourceHealth['health_status'], string>;
  rolloutStageLabels: Record<string, string>;
  rolloutStageBadgeClasses: Record<string, string>;
  documentPolicyLabels: Record<string, string>;
  crawlRunBadgeClasses: Record<string, string>;
  onTriggerCrawl: (sourceId: number) => void;
  onToggleCandidates: (crawlRunId: number) => void;
  renderCandidateDetail: (crawlRunId: number) => ReactNode;
  getSourceReviewReason: (source: SourceHealth) => string | null;
  getLatestRun: (source: SourceHealth) => SourceHealth['recent_crawl_runs'][number] | null;
  getSaveRate: (run: SourceHealth['recent_crawl_runs'][number]) => number;
  formatDateTime: (value: string | null) => string;
  formatDuration: (value: number | null) => string;
};

type CrawlQualitySummary = {
  metrics: { label: string; value: string }[];
  skips: string[];
};

function parseCrawlQualitySummary(text: string | null): CrawlQualitySummary | null {
  if (!text?.startsWith('质量检查：')) {
    return null;
  }

  const body = text.replace(/^质量检查：/, '');
  const parts = body
    .split('；')
    .map((part) => part.trim())
    .filter(Boolean);
  const metrics: CrawlQualitySummary['metrics'] = [];
  const skips: string[] = [];

  parts.forEach((part) => {
    if (part.startsWith('跳过：')) {
      skips.push(
        ...part
          .replace(/^跳过：/, '')
          .split('，')
          .map((item) => item.trim())
          .filter(Boolean)
      );
      return;
    }

    const metricMatch = part.match(/^(原始候选|有效去重后|入库)\s+(\d+)\s+条$/);
    if (metricMatch) {
      metrics.push({
        label: metricMatch[1],
        value: metricMatch[2],
      });
    }
  });

  if (metrics.length === 0 && skips.length === 0) {
    return null;
  }

  return { metrics, skips };
}

function CrawlRunQualitySummary({ error }: { error: string | null }) {
  const summary = parseCrawlQualitySummary(error);

  if (!summary) {
    return <span className="crawl-run-error">{error ?? '无'}</span>;
  }

  return (
    <div className="crawl-quality-summary">
      {summary.metrics.length > 0 ? (
        <div className="crawl-quality-metrics">
          {summary.metrics.map((metric) => (
            <span key={metric.label} className="crawl-quality-metric">
              <span>{metric.label}</span>
              <strong>{metric.value}</strong>
            </span>
          ))}
        </div>
      ) : null}
      {summary.skips.length > 0 ? (
        <div className="crawl-quality-skips">
          {summary.skips.map((skip) => (
            <span key={skip} className="badge">
              {skip}
            </span>
          ))}
        </div>
      ) : null}
      <p className="crawl-run-error">{error}</p>
    </div>
  );
}

export function SourceHealthList({
  sources,
  loading,
  hasActiveFilter,
  crawlingSourceId,
  expandedRunId,
  candidateLoadingRunId,
  crawlableSourceTypes,
  healthLabels,
  healthBadgeClasses,
  rolloutStageLabels,
  rolloutStageBadgeClasses,
  documentPolicyLabels,
  crawlRunBadgeClasses,
  onTriggerCrawl,
  onToggleCandidates,
  renderCandidateDetail,
  getSourceReviewReason,
  getLatestRun,
  getSaveRate,
  formatDateTime,
  formatDuration,
}: SourceHealthListProps) {
  if (sources.length === 0 && !loading) {
    return <p>{hasActiveFilter ? '暂无匹配来源。' : '暂无来源。'}</p>;
  }

  return (
    <ul className="source-health-list">
      {sources.map((source) => {
        const sourceReviewReason = getSourceReviewReason(source);
        const latestRun = getLatestRun(source);

        return (
          <li key={source.id} className="source-health-item">
            <div className="source-health-main">
              <div className="source-health-title">
                <div>
                  <strong>{source.think_tank_name}</strong>
                  <span className="muted"> / {source.think_tank_country}</span>
                </div>
                <span className={healthBadgeClasses[source.health_status]}>{healthLabels[source.health_status]}</span>
              </div>
              <a href={source.url} target="_blank" rel="noreferrer">
                {source.url}
              </a>
              <div className="source-health-priority">
                <span className="badge">{priorityTierLabels[source.think_tank_priority_tier]}</span>
                <span className="badge">{regionFocusLabels[source.think_tank_region_focus]}</span>
                <span className={rolloutStageBadgeClasses[source.rollout_stage] ?? 'badge'}>
                  {rolloutStageLabels[source.rollout_stage] ?? source.rollout_stage}
                </span>
              </div>
              <p>{source.health_reason}</p>

              {sourceReviewReason ? (
                <p className="source-attention">需处理：{sourceReviewReason}</p>
              ) : (
                <p className="source-stable">当前无需人工处理，继续观察自动抓取结果。</p>
              )}

              <div className="source-health-actions">
                <button
                  type="button"
                  onClick={() => onTriggerCrawl(source.id)}
                  disabled={
                    crawlingSourceId === source.id ||
                    !source.is_active ||
                    !crawlableSourceTypes.has(source.source_type as SourceCreateInput['source_type'])
                  }
                >
                  {crawlingSourceId === source.id ? '提交中……' : '手动重试'}
                </button>
                <span className="muted">
                  最近发现 {latestRun?.found_count ?? 0}，入库 {latestRun?.saved_count ?? 0}
                </span>
              </div>
            </div>

            <dl className="source-health-meta">
              <div>
                <dt>健康状态</dt>
                <dd>
                  <span className={healthBadgeClasses[source.health_status]}>{healthLabels[source.health_status]}</span>
                </dd>
              </div>
              <div>
                <dt>来源类型</dt>
                <dd>{source.source_type}</dd>
              </div>
              <div>
                <dt>优先级</dt>
                <dd>
                  <span className="badge">{priorityTierLabels[source.think_tank_priority_tier]}</span>
                </dd>
              </div>
              <div>
                <dt>区域</dt>
                <dd>{regionFocusLabels[source.think_tank_region_focus]}</dd>
              </div>
              <div>
                <dt>校对</dt>
                <dd>{source.think_tank_is_verified ? '已校对' : '待校对'}</dd>
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
              <div>
                <dt>试运行策略</dt>
                <dd>
                  <span className={rolloutStageBadgeClasses[source.rollout_stage] ?? 'badge'}>
                    {rolloutStageLabels[source.rollout_stage] ?? source.rollout_stage}
                  </span>
                </dd>
              </div>
              <div>
                <dt>文档口径</dt>
                <dd>{documentPolicyLabels[source.document_policy] ?? source.document_policy}</dd>
              </div>
            </dl>

            <p className="source-advice">{source.diagnosis_advice}</p>
            <p className="source-advice">{source.rollout_advice}</p>

            {source.last_error ? <p className="source-error">{source.last_error}</p> : null}

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
                        <th>保存率</th>
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
                              <span className={crawlRunBadgeClasses[run.status] ?? 'badge'}>
                                {crawlRunStatusLabels[run.status] ?? run.status}
                              </span>
                            </td>
                            <td>{run.found_count}</td>
                            <td>{run.saved_count}</td>
                            <td>{getSaveRate(run)}%</td>
                            <td>{formatDuration(run.duration_seconds)}</td>
                            <td>
                              <CrawlRunQualitySummary error={run.error} />
                            </td>
                            <td>
                              <button
                                type="button"
                                onClick={() => onToggleCandidates(run.id)}
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
                              <td colSpan={8}>
                                <div className="candidate-detail">{renderCandidateDetail(run.id)}</div>
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
          </li>
        );
      })}
    </ul>
  );
}
