'use client';

import { type CrawlCandidate, type CrawlCandidateStatistics } from '@/lib/institution';
import { type ReportProcessingOperation } from '@/lib/report-error';
import { crawlCandidateStatusLabels, type CrawlCandidateStatus } from '@/lib/status';
import { LLMAuthorizationControl } from '@/components/llm-authorization-control';
import { ProcessingErrorDisclosure } from '@/components/processing-error-disclosure';

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
  canAuthorize: boolean;
  onFilterChange: (crawlRunId: number, field: keyof CandidateFilters, value: string) => void;
  onApplyFilters: (crawlRunId: number, filters: CandidateFilters) => void;
  onExportCandidates: (crawlRunId: number) => void;
  onLoadMoreCandidates: (crawlRunId: number) => void;
};

type CandidateReasonDisplay = {
  label: string;
  groupLabel: string | null;
  helper: string | null;
  badgeClassName: string;
};

type CandidateQualitySummaryItem = {
  key: string;
  label: string;
  value: number;
  helper: string;
  className: string;
  targetFilters: CandidateFilters;
};

const duplicateReasonLabels = new Set(['已入库重复', '同一来源内重复', '并发重复入库']);
const savedDuplicateReasonLabels = new Set(['已入库重复']);

function getCandidateErrorOperation(candidate: CrawlCandidate): ReportProcessingOperation {
  const error = candidate.error ?? '';
  if (candidate.skip_reason_label === '涉华判断失败' || /LLM|AI |涉华判断|外发总开关|未授权|缺少授权/.test(error)) {
    return 'ai';
  }

  return 'fetch';
}

function CandidateNote({ candidate, helper }: { candidate: CrawlCandidate; helper: string | null }) {
  const relevanceReason = candidate.relevance_reason?.trim() || null;
  const candidateError = candidate.error?.trim() || null;
  const hasDistinctError = candidateError !== null && candidateError !== relevanceReason;
  const operation = getCandidateErrorOperation(candidate);

  return (
    <div className="candidate-note">
      {hasDistinctError ? (
        <ProcessingErrorDisclosure
          error={candidateError}
          operation={operation}
          label={operation === 'ai' ? 'AI 判断' : '检查结果'}
          compact
          tone="neutral"
        />
      ) : relevanceReason ? (
        <span>{relevanceReason}</span>
      ) : (
        <span>无</span>
      )}
      {hasDistinctError && relevanceReason ? <span>{relevanceReason}</span> : null}
      {helper ? <small>{helper}</small> : null}
    </div>
  );
}

function getCandidateBadgeClass(status: string | null): string {
  if (status === 'discovered' || status === 'pending_relevance' || status === 'skipped' || status === 'saved') {
    const candidateBadgeClasses: Record<CrawlCandidateStatus, string> = {
      discovered: 'badge',
      pending_relevance: 'badge',
      skipped: 'badge badge-warning',
      saved: 'badge badge-success',
    };

    return candidateBadgeClasses[status];
  }

  return 'badge';
}

function getCandidateReasonDisplay(label: string | null, error?: string | null): CandidateReasonDisplay {
  if (!label) {
    return {
      label: '无',
      groupLabel: null,
      helper: null,
      badgeClassName: 'badge',
    };
  }

  if (label === '已入库重复' || label === '同一来源内重复' || label === '并发重复入库') {
    return {
      label,
      groupLabel: '重复候选',
      helper: '已有记录，无需再次入库。',
      badgeClassName: 'badge candidate-reason-badge candidate-reason-duplicate',
    };
  }

  if (label === '未发现 PDF 链接') {
    const isPreflight = error?.includes('发现阶段预检') ?? false;

    return {
      label,
      groupLabel: isPreflight ? '发现阶段预检' : '文档检查',
      helper: isPreflight ? '详情页未发现 PDF，已提前跳过。' : '详情页未发现可下载 PDF。',
      badgeClassName: 'badge candidate-reason-badge candidate-reason-preflight',
    };
  }

  if (label === 'PDF 页数不足') {
    return {
      label,
      groupLabel: '文档门槛',
      helper: 'PDF 低于 20 页要求。',
      badgeClassName: 'badge candidate-reason-badge candidate-reason-short',
    };
  }

  if (label === 'PDF 文本不足' || label === 'PDF 获取或解析失败' || label === 'PDF 获取或页数/文本检查失败') {
    return {
      label,
      groupLabel: '文档检查',
      helper: 'PDF 获取、解析或正文抽取未通过。',
      badgeClassName: 'badge candidate-reason-badge candidate-reason-document',
    };
  }

  if (label === '非涉华') {
    return {
      label,
      groupLabel: '涉华判断',
      helper: '涉华相关性未通过。',
      badgeClassName: 'badge candidate-reason-badge candidate-reason-relevance',
    };
  }

  if (label === '涉华判断失败') {
    return {
      label,
      groupLabel: 'AI 判断',
      helper: '涉华判断环节异常。',
      badgeClassName: 'badge candidate-reason-badge candidate-reason-ai',
    };
  }

  if (label === '无效 URL') {
    return {
      label,
      groupLabel: '入口异常',
      helper: '候选链接无法规范化。',
      badgeClassName: 'badge candidate-reason-badge candidate-reason-danger',
    };
  }

  return {
    label,
    groupLabel: null,
    helper: null,
    badgeClassName: 'badge candidate-reason-badge',
  };
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

function buildCandidateReasonSelectOptions(
  baseOptions: string[],
  loadedOptions: string[],
  statistics: CrawlCandidateStatistics | undefined
): string[] {
  const options = new Set<string>(baseOptions);

  statistics?.by_skip_reason.forEach((item) => {
    if (item.label) {
      options.add(item.label);
    }
  });
  loadedOptions.forEach((option) => options.add(option));

  return [...options];
}

function getStatusCount(
  statistics: CrawlCandidateStatistics | undefined,
  candidates: CrawlCandidate[],
  status: CrawlCandidateStatus
): number {
  const count = statistics?.by_status.find((item) => item.code === status)?.count;

  if (count !== undefined) {
    return count;
  }

  return candidates.filter((candidate) => candidate.status === status).length;
}

function getReasonCount(
  statistics: CrawlCandidateStatistics | undefined,
  candidates: CrawlCandidate[],
  labels: Set<string>
): number {
  if (statistics) {
    return statistics.by_skip_reason.reduce((sum, item) => sum + (labels.has(item.label) ? item.count : 0), 0);
  }

  return candidates.filter(
    (candidate) => candidate.skip_reason_label !== null && labels.has(candidate.skip_reason_label)
  ).length;
}

function buildCandidateQualitySummary(
  candidates: CrawlCandidate[],
  totalCandidates: number,
  statistics: CrawlCandidateStatistics | undefined
): CandidateQualitySummaryItem[] {
  const total = statistics?.total ?? totalCandidates;
  const saved = getStatusCount(statistics, candidates, 'saved');
  const duplicate = getReasonCount(statistics, candidates, savedDuplicateReasonLabels);
  const shortPdf = getReasonCount(statistics, candidates, new Set(['PDF 页数不足']));
  const missingPdf = getReasonCount(statistics, candidates, new Set(['未发现 PDF 链接']));
  const preflightNoPdf = candidates.filter(
    (candidate) =>
      candidate.skip_reason_label === '未发现 PDF 链接' && (candidate.error?.includes('发现阶段预检') ?? false)
  ).length;
  const loadedComplete = candidates.length >= total;
  const preflightHelper =
    preflightNoPdf > 0
      ? loadedComplete
        ? '发现阶段预检，已提前跳过'
        : `已加载 ${preflightNoPdf} 条预检；无 PDF 共 ${missingPdf} 条`
      : missingPdf > 0 && candidates.length === 0
        ? `无 PDF 共 ${missingPdf} 条`
        : '详情页未发现 PDF';

  return [
    {
      key: 'total',
      label: '全部候选',
      value: total,
      helper: `已加载 ${candidates.length} 条`,
      className: 'candidate-quality-card-total',
      targetFilters: {
        status: '',
        reason: '',
      },
    },
    {
      key: 'saved',
      label: '新增入库',
      value: saved,
      helper: saved > 0 ? '已进入报告库' : '本轮无新增入库',
      className: 'candidate-quality-card-saved',
      targetFilters: {
        status: 'saved',
        reason: '',
      },
    },
    {
      key: 'preflight',
      label: '无 PDF',
      value: missingPdf,
      helper: preflightHelper,
      className: 'candidate-quality-card-preflight',
      targetFilters: {
        status: 'skipped',
        reason: '未发现 PDF 链接',
      },
    },
    {
      key: 'short-pdf',
      label: '短 PDF',
      value: shortPdf,
      helper: '低于 20 页门槛',
      className: 'candidate-quality-card-short',
      targetFilters: {
        status: 'skipped',
        reason: 'PDF 页数不足',
      },
    },
    {
      key: 'duplicate',
      label: '已入库重复',
      value: duplicate,
      helper: '报告库已有记录',
      className: 'candidate-quality-card-duplicate',
      targetFilters: {
        status: 'skipped',
        reason: '已入库重复',
      },
    },
  ];
}

function isSameCandidateFilter(left: CandidateFilters, right: CandidateFilters): boolean {
  return left.status === right.status && left.reason === right.reason;
}

function filterCandidates(candidates: CrawlCandidate[], filters: CandidateFilters): CrawlCandidate[] {
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
  canAuthorize,
  onFilterChange,
  onApplyFilters,
  onExportCandidates,
  onLoadMoreCandidates,
}: CandidateDetailProps) {
  const loadedReasonOptions = buildLoadedCandidateReasonOptions(candidates);
  const reasonSelectOptions = buildCandidateReasonSelectOptions(
    candidateReasonOptions,
    loadedReasonOptions,
    statistics
  );
  const qualitySummaryItems = buildCandidateQualitySummary(candidates, totalCandidates, statistics);
  const filteredCandidates = filterCandidates(candidates, filters);
  const knownCandidateTotal = statistics?.total ?? totalCandidates;
  const hasAnyCandidates = knownCandidateTotal > 0 || candidates.length > 0;

  if (loading) {
    return <p className="muted">正在加载候选明细……</p>;
  }

  if (!hasAnyCandidates) {
    return <p className="muted">这次抓取暂无候选明细。历史运行不会自动回填。</p>;
  }

  return (
    <>
      <div className="candidate-quality-summary" aria-label="候选质量摘要">
        {qualitySummaryItems.map((item) => (
          <button
            type="button"
            key={item.key}
            className={`candidate-quality-card ${item.className}`}
            onClick={() => onApplyFilters(crawlRunId, item.targetFilters)}
            aria-pressed={isSameCandidateFilter(filters, item.targetFilters)}
          >
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            <small>{item.helper}</small>
          </button>
        ))}
      </div>

      <div className="candidate-summary">
        <span className="badge">全部 {statistics?.total ?? totalCandidates}</span>
        {statistics?.by_status.map((item, index) => (
          <span key={`${item.code ?? item.label}-${index}`} className={getCandidateBadgeClass(item.code)}>
            {item.label} {item.count}
          </span>
        ))}
        {statistics?.by_content_kind.map((item, index) => (
          <span key={`${item.code ?? item.label}-${index}`} className="badge">
            {item.label} {item.count}
          </span>
        ))}
      </div>

      {statistics?.by_skip_reason.length ? (
        <div className="candidate-reason-summary">
          {statistics.by_skip_reason.map((item) => (
            <span
              key={`${item.code ?? 'reason'}-${item.label}`}
              className={getCandidateReasonDisplay(item.label).badgeClassName}
            >
              {item.label} {item.count}
            </span>
          ))}
        </div>
      ) : loadedReasonOptions.length > 0 ? (
        <div className="candidate-reason-summary">
          {loadedReasonOptions.map((reason) => (
            <span key={reason} className={getCandidateReasonDisplay(reason).badgeClassName}>
              {reason} {candidates.filter((candidate) => candidate.skip_reason_label === reason).length}
            </span>
          ))}
        </div>
      ) : null}

      <div className="candidate-filters">
        <label>
          状态
          <select value={filters.status} onChange={(event) => onFilterChange(crawlRunId, 'status', event.target.value)}>
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
            onChange={(event) => onFilterChange(crawlRunId, 'reason', event.target.value)}
            disabled={filters.status !== '' && filters.status !== 'skipped'}
          >
            <option value="">全部原因</option>
            {reasonSelectOptions.map((reason) => (
              <option key={reason} value={reason}>
                {reason}
              </option>
            ))}
          </select>
        </label>

        <span className="muted">
          当前筛选共 {totalCandidates} 条；已加载 {candidates.length} 条；当前显示 {filteredCandidates.length} 条
        </span>

        <button type="button" onClick={() => onExportCandidates(crawlRunId)} disabled={exporting}>
          {exporting ? '导出中……' : '导出 CSV'}
        </button>
      </div>

      {filteredCandidates.length === 0 ? (
        <p className="muted">当前筛选条件下暂无候选。</p>
      ) : (
        <table className="candidate-table">
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
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {filteredCandidates.map((candidate) => {
              const reasonDisplay = getCandidateReasonDisplay(candidate.skip_reason_label, candidate.error);

              return (
                <tr key={candidate.id} className="candidate-table-row">
                  <td className="candidate-title" data-label="标题">
                    {candidate.title ?? '无标题'}
                  </td>
                  <td data-label="状态">
                    <span className={getCandidateBadgeClass(candidate.status)}>
                      {crawlCandidateStatusLabels[candidate.status] ?? candidate.status}
                    </span>
                  </td>
                  <td data-label="跳过原因">
                    <div className="candidate-reason-cell">
                      <span className={reasonDisplay.badgeClassName}>{reasonDisplay.label}</span>
                      {reasonDisplay.groupLabel ? <small>{reasonDisplay.groupLabel}</small> : null}
                    </div>
                  </td>
                  <td data-label="类型">
                    {candidate.content_kind === 'web_article'
                      ? '网页长文'
                      : candidate.content_kind === 'pdf'
                        ? 'PDF'
                        : '未知'}
                  </td>
                  <td data-label="页数">{candidate.page_count ?? '暂无'}</td>
                  <td data-label="涉华">
                    {candidate.is_china_related === null ? '未判断' : candidate.is_china_related ? '是' : '否'}
                  </td>
                  <td data-label="链接">
                    <a href={candidate.url} target="_blank" rel="noreferrer">
                      打开
                    </a>
                  </td>
                  <td data-label="说明">
                    <CandidateNote candidate={candidate} helper={reasonDisplay.helper} />
                  </td>
                  <td className="candidate-action-cell" data-label="操作">
                    {canAuthorize && candidate.status === 'pending_relevance' ? (
                      <LLMAuthorizationControl scope="relevance_sample" targetId={candidate.id} compact />
                    ) : (
                      <span className="muted">无</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {candidates.length < totalCandidates ? (
        <div className="candidate-load-more">
          <button type="button" onClick={() => onLoadMoreCandidates(crawlRunId)} disabled={loading}>
            {loading ? '加载中……' : `加载更多（剩余 ${totalCandidates - candidates.length} 条）`}
          </button>
        </div>
      ) : null}
    </>
  );
}

export type { CandidateFilters };
