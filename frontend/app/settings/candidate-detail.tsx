'use client';

import {
  type CrawlCandidate,
  type CrawlCandidateStatistics,
} from '@/lib/institution';
import {
  crawlCandidateStatusLabels,
  type CrawlCandidateStatus,
} from '@/lib/status';

type CandidateFilters = {
  status: CrawlCandidateStatus | '';
  reason: string;
};

type CandidateDetailProps = {
  crawlRunId: number;
  candidates: CrawlCandidate[];
  totalCandidates: number;
  statistics: CrawlCandidateStatistics | undefined;
  filters: CandidateFilters;
  loading: boolean;
  exporting: boolean;
  candidateReasonOptions: string[];
  onFilterChange: (
    crawlRunId: number,
    field: keyof CandidateFilters,
    value: string
  ) => void;
  onExportCandidates: (crawlRunId: number) => void;
  onLoadMoreCandidates: (crawlRunId: number) => void;
};

function getCandidateBadgeClass(status: string | null): string {
  if (
    status === 'discovered' ||
    status === 'skipped' ||
    status === 'saved'
  ) {
    const candidateBadgeClasses: Record<CrawlCandidateStatus, string> = {
      discovered: 'badge',
      skipped: 'badge badge-warning',
      saved: 'badge badge-success',
    };

    return candidateBadgeClasses[status];
  }

  return 'badge';
}

function buildLoadedCandidateReasonOptions(
  candidates: CrawlCandidate[]
): string[] {
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

export function CandidateDetail({
  crawlRunId,
  candidates,
  totalCandidates,
  statistics,
  filters,
  loading,
  exporting,
  candidateReasonOptions,
  onFilterChange,
  onExportCandidates,
  onLoadMoreCandidates,
}: CandidateDetailProps) {
  const loadedReasonOptions = buildLoadedCandidateReasonOptions(candidates);
  const filteredCandidates = filterCandidates(candidates, filters);

  if (loading) {
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
            className={getCandidateBadgeClass(item.code)}
          >
            {item.label} {item.count}
          </span>
        ))}
        {statistics?.by_content_kind.map((item) => (
          <span key={item.code ?? item.label} className="badge">
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
              onFilterChange(crawlRunId, 'status', event.target.value)
            }
          >
            <option value="">全部状态</option>
            {Object.entries(crawlCandidateStatusLabels).map(([value, label]) => (
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
              onFilterChange(crawlRunId, 'reason', event.target.value)
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
          onClick={() => onExportCandidates(crawlRunId)}
          disabled={exporting}
        >
          {exporting ? '导出中……' : '导出 CSV'}
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
              <th>类型</th>
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
                  <span className={getCandidateBadgeClass(candidate.status)}>
                    {crawlCandidateStatusLabels[candidate.status] ??
                      candidate.status}
                  </span>
                </td>
                <td>{candidate.skip_reason_label ?? '无'}</td>
                <td>
                  {candidate.content_kind === 'web_article'
                    ? '网页长文'
                    : candidate.content_kind === 'pdf'
                      ? 'PDF'
                      : '未知'}
                </td>
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
            onClick={() => onLoadMoreCandidates(crawlRunId)}
            disabled={loading}
          >
            {loading
              ? '加载中……'
              : `加载更多（剩余 ${totalCandidates - candidates.length} 条）`}
          </button>
        </div>
      ) : null}
    </>
  );
}

export type { CandidateFilters };
