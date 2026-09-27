'use client';

import { type FormEvent } from 'react';

import { type Source, type ThinkTank } from '@/lib/institution';
import {
  reportAIStatusLabels,
  reportContentKindLabels,
  reportDeliverableStatusLabels,
  reportReviewStatusLabels,
  type ReportAIStatus,
  type ReportContentKind,
  type ReportDeliverableStatus,
  type ReportReviewStatus,
} from '@/lib/status';

import {
  ActiveFilterSummary,
  type ActiveFilterItem,
} from './active-filter-summary';
import {
  getSourceFilterLabel,
  ReportFilterFields,
} from './report-filter-fields';
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

      <ReportFilterFields
        loading={loading}
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
        onReviewStatusChange={onReviewStatusChange}
        onAIStatusChange={onAIStatusChange}
        onContentKindChange={onContentKindChange}
        onDeliverableStatusChange={onDeliverableStatusChange}
        onThinkTankChange={onThinkTankChange}
        onSourceChange={onSourceChange}
        onPreviousPage={onPreviousPage}
        onNextPage={onNextPage}
      />
    </>
  );
}
