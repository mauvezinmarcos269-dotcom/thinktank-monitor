'use client';

import { type FormEvent } from 'react';

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
import {
  ActiveFilterSummary,
  type ActiveFilterItem,
} from './active-filter-summary';
import { WorkflowShortcuts } from './workflow-shortcuts';

type ReportFilterBarProps = {
  searchDraft: string;
  keywordFilter: string;
  loading: boolean;
  busyMessage?: string;
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
  onSearchDraftChange: (value: string) => void;
  onSearchSubmit: (event?: FormEvent<HTMLFormElement>) => void;
  onSearchClear: () => void;
  onResetFilters: () => void;
  onReviewStatusChange: (value: ReportReviewStatus | '') => void;
  onAIStatusChange: (value: ReportAIStatus | '') => void;
  onContentKindChange: (value: ReportContentKind | '') => void;
  onDeliverableStatusChange: (value: ReportDeliverableStatus | '') => void;
  onThinkTankChange: (value: number | '') => void;
  onSourceChange: (value: number | '') => void;
  onWorkflowShortcut: (shortcut: ReportWorkflowShortcut) => void;
  onPreviousPage: () => void;
  onNextPage: () => void;
};

export type ReportWorkflowShortcut =
  | 'all'
  | 'teacher_review'
  | 'ready_export'
  | 'needs_rerun';

function getSourceFilterLabel(source: Source): string {
  return `${formatSourceUrl(source.url)} / ${
    sourceTypeLabels[source.source_type] ?? source.source_type
  }`;
}

export function ReportFilterBar({
  searchDraft,
  keywordFilter,
  loading,
  busyMessage,
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
  onSearchDraftChange,
  onSearchSubmit,
  onSearchClear,
  onResetFilters,
  onReviewStatusChange,
  onAIStatusChange,
  onContentKindChange,
  onDeliverableStatusChange,
  onThinkTankChange,
  onSourceChange,
  onWorkflowShortcut,
  onPreviousPage,
  onNextPage,
}: ReportFilterBarProps) {
  const selectedSource = sourceFilter
    ? sourceOptions.find((source) => source.id === sourceFilter)
    : null;
  const selectedThinkTank = thinkTankFilter
    ? thinkTanks.find((thinkTank) => thinkTank.id === thinkTankFilter)
    : null;
  const activeFilterItems: ActiveFilterItem[] = [
    keywordFilter
      ? {
          key: 'keyword',
          label: `关键词：${keywordFilter}`,
          onClear: onSearchClear,
        }
      : null,
    reviewStatusFilter
      ? {
          key: 'review_status',
          label: `复核：${reportReviewStatusLabels[reviewStatusFilter]}`,
          onClear: () => onReviewStatusChange(''),
        }
      : null,
    aiStatusFilter
      ? {
          key: 'ai_status',
          label: `AI：${reportAIStatusLabels[aiStatusFilter]}`,
          onClear: () => onAIStatusChange(''),
        }
      : null,
    contentKindFilter
      ? {
          key: 'content_kind',
          label: `类型：${reportContentKindLabels[contentKindFilter]}`,
          onClear: () => onContentKindChange(''),
        }
      : null,
    deliverableStatusFilter
      ? {
          key: 'deliverable_status',
          label: `成果：${reportDeliverableStatusLabels[deliverableStatusFilter]}`,
          onClear: () => onDeliverableStatusChange(''),
        }
      : null,
    thinkTankFilter
      ? {
          key: 'think_tank',
          label: `智库：${selectedThinkTank?.name ?? thinkTankFilter}`,
          onClear: () => onThinkTankChange(''),
        }
      : null,
    sourceFilter
      ? {
          key: 'source',
          label: `来源：${
            selectedSource ? getSourceFilterLabel(selectedSource) : sourceFilter
          }`,
          onClear: () => onSourceChange(''),
        }
      : null,
  ].filter((item): item is ActiveFilterItem => item !== null);
  const hasActiveFilter = activeFilterItems.length > 0;
  const hasExtraShortcutFilter = Boolean(
    keywordFilter ||
      contentKindFilter ||
      deliverableStatusFilter ||
      thinkTankFilter ||
      sourceFilter
  );
  const activeShortcut =
    !hasExtraShortcutFilter &&
    reviewStatusFilter === 'pending_review' &&
    aiStatusFilter === 'success' &&
    deliverableStatusFilter === 'complete'
      ? 'teacher_review'
      : !hasExtraShortcutFilter &&
          reviewStatusFilter === 'needs_rerun' &&
          !aiStatusFilter &&
          !deliverableStatusFilter
        ? 'needs_rerun'
        : !keywordFilter &&
            !contentKindFilter &&
            !thinkTankFilter &&
            !sourceFilter &&
            !reviewStatusFilter &&
            aiStatusFilter === 'success' &&
            deliverableStatusFilter === 'complete'
          ? 'ready_export'
          : !hasActiveFilter
            ? 'all'
            : '';

  return (
    <>
      <form className="report-search-bar" onSubmit={onSearchSubmit}>
        <label>
          关键词搜索
          <input
            value={searchDraft}
            onChange={(event) => onSearchDraftChange(event.target.value)}
            placeholder="输入报告 ID、标题、智库、链接关键词，如 381 / China / Brookings"
            disabled={loading}
          />
        </label>
        <button type="submit" disabled={loading}>
          搜索
        </button>
        {keywordFilter ? (
          <button type="button" onClick={onSearchClear} disabled={loading}>
            清空搜索
          </button>
        ) : null}
        <button type="button" onClick={onResetFilters} disabled={loading}>
          重置筛选
        </button>
      </form>

      {busyMessage ? (
        <div className="filter-busy-note" role="status">
          {busyMessage}
        </div>
      ) : null}

      <WorkflowShortcuts
        activeShortcut={activeShortcut}
        loading={loading}
        onWorkflowShortcut={onWorkflowShortcut}
        onResetFilters={onResetFilters}
      />

      <ActiveFilterSummary
        items={activeFilterItems}
        loading={loading}
        onResetFilters={onResetFilters}
      />

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
    </>
  );
}
