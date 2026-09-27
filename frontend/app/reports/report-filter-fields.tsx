'use client';

import { type Source, type ThinkTank } from '@/lib/institution';
import {
  reportAIStatusLabels,
  reportContentKindLabels,
  reportDeliverableStatusLabels,
  reportReviewStatusLabels,
  sourceTypeLabels,
  type ReportAIStatus,
  type ReportContentKind,
  type ReportDeliverableStatus,
  type ReportReviewStatus,
} from '@/lib/status';

import {
  aiStatusOptions,
  contentKindOptions,
  formatSourceUrl,
  reviewStatusOptions,
} from './report-page-utils';

type ReportFilterFieldsProps = {
  loading: boolean;
  totalReports: number;
  page: number;
  totalPages: number;
  reviewStatusFilter: ReportReviewStatus | '';
  aiStatusFilter: ReportAIStatus | '';
  contentKindFilter: ReportContentKind | '';
  deliverableStatusFilter: ReportDeliverableStatus | '';
  thinkTankFilter: number | '';
  sourceFilter: number | '';
  thinkTanks: ThinkTank[];
  sourceOptions: Source[];
  onReviewStatusChange: (value: ReportReviewStatus | '') => void;
  onAIStatusChange: (value: ReportAIStatus | '') => void;
  onContentKindChange: (value: ReportContentKind | '') => void;
  onDeliverableStatusChange: (value: ReportDeliverableStatus | '') => void;
  onThinkTankChange: (value: number | '') => void;
  onSourceChange: (value: number | '') => void;
  onPreviousPage: () => void;
  onNextPage: () => void;
};

export function getSourceFilterLabel(source: Source): string {
  return `${formatSourceUrl(source.url)} / ${
    sourceTypeLabels[source.source_type] ?? source.source_type
  }`;
}

export function ReportFilterFields({
  loading,
  totalReports,
  page,
  totalPages,
  reviewStatusFilter,
  aiStatusFilter,
  contentKindFilter,
  deliverableStatusFilter,
  thinkTankFilter,
  sourceFilter,
  thinkTanks,
  sourceOptions,
  onReviewStatusChange,
  onAIStatusChange,
  onContentKindChange,
  onDeliverableStatusChange,
  onThinkTankChange,
  onSourceChange,
  onPreviousPage,
  onNextPage,
}: ReportFilterFieldsProps) {
  return (
    <div className="toolbar">
      <p className="muted">
        共 {totalReports} 篇，第 {page} / {totalPages} 页
      </p>
      <label>
        复核
        <select
          value={reviewStatusFilter}
          onChange={(event) =>
            onReviewStatusChange(event.target.value as ReportReviewStatus | '')
          }
          disabled={loading}
        >
          <option value="">全部</option>
          {reviewStatusOptions.map((status) => (
            <option key={status} value={status}>
              {reportReviewStatusLabels[status]}
            </option>
          ))}
        </select>
      </label>
      <label>
        AI
        <select
          value={aiStatusFilter}
          onChange={(event) =>
            onAIStatusChange(event.target.value as ReportAIStatus | '')
          }
          disabled={loading}
        >
          <option value="">全部</option>
          {aiStatusOptions.map((status) => (
            <option key={status} value={status}>
              {reportAIStatusLabels[status]}
            </option>
          ))}
        </select>
      </label>
      <label>
        类型
        <select
          value={contentKindFilter}
          onChange={(event) =>
            onContentKindChange(event.target.value as ReportContentKind | '')
          }
          disabled={loading}
        >
          <option value="">全部</option>
          {contentKindOptions.map((kind) => (
            <option key={kind} value={kind}>
              {reportContentKindLabels[kind]}
            </option>
          ))}
        </select>
      </label>
      <label>
        成果
        <select
          value={deliverableStatusFilter}
          onChange={(event) =>
            onDeliverableStatusChange(
              event.target.value as ReportDeliverableStatus | ''
            )
          }
          disabled={loading}
        >
          <option value="">全部</option>
          <option value="complete">
            {reportDeliverableStatusLabels.complete}
          </option>
          <option value="partial">
            {reportDeliverableStatusLabels.partial}
          </option>
          <option value="empty">{reportDeliverableStatusLabels.empty}</option>
        </select>
      </label>
      <label>
        智库
        <select
          value={thinkTankFilter}
          onChange={(event) =>
            onThinkTankChange(
              event.target.value ? Number(event.target.value) : ''
            )
          }
          disabled={loading}
        >
          <option value="">全部</option>
          {thinkTanks.map((thinkTank) => (
            <option key={thinkTank.id} value={thinkTank.id}>
              {thinkTank.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        来源
        <select
          value={sourceFilter}
          onChange={(event) =>
            onSourceChange(event.target.value ? Number(event.target.value) : '')
          }
          disabled={loading}
        >
          <option value="">全部</option>
          {sourceOptions.map((source) => (
            <option key={source.id} value={source.id}>
              {getSourceFilterLabel(source)}
            </option>
          ))}
        </select>
      </label>
      <button
        type="button"
        onClick={onPreviousPage}
        disabled={page <= 1 || loading}
      >
        上一页
      </button>
      <button
        type="button"
        onClick={onNextPage}
        disabled={page >= totalPages || loading}
      >
        下一页
      </button>
    </div>
  );
}
