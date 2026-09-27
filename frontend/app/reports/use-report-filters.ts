'use client';

import { type FormEvent, useState } from 'react';

import {
  type ReportAIStatus,
  type ReportContentKind,
  type ReportDeliverableStatus,
  type ReportReviewStatus,
} from '@/lib/status';

import { type ReportWorkflowShortcut } from './report-filter-bar';

type ResetReportListState = () => void;

export function useReportFilters(resetReportListState: ResetReportListState) {
  const [page, setPage] = useState(1);
  const [reviewStatusFilter, setReviewStatusFilter] = useState<
    ReportReviewStatus | ''
  >('');
  const [aiStatusFilter, setAIStatusFilter] = useState<ReportAIStatus | ''>('');
  const [contentKindFilter, setContentKindFilter] = useState<
    ReportContentKind | ''
  >('');
  const [deliverableStatusFilter, setDeliverableStatusFilter] = useState<
    ReportDeliverableStatus | ''
  >('');
  const [searchDraft, setSearchDraft] = useState('');
  const [keywordFilter, setKeywordFilter] = useState('');
  const [thinkTankFilter, setThinkTankFilter] = useState<number | ''>('');
  const [sourceFilter, setSourceFilter] = useState<number | ''>('');

  function resetReportListSelection() {
    setPage(1);
    resetReportListState();
  }

  function handleReviewStatusFilterChange(value: ReportReviewStatus | '') {
    setReviewStatusFilter(value);
    resetReportListSelection();
  }

  function handleAIStatusFilterChange(value: ReportAIStatus | '') {
    setAIStatusFilter(value);
    resetReportListSelection();
  }

  function handleContentKindFilterChange(value: ReportContentKind | '') {
    setContentKindFilter(value);
    resetReportListSelection();
  }

  function handleDeliverableStatusFilterChange(
    value: ReportDeliverableStatus | ''
  ) {
    setDeliverableStatusFilter(value);
    resetReportListSelection();
  }

  function handleKeywordFilterChange(value: string) {
    setKeywordFilter(value);
    resetReportListSelection();
  }

  function handleSearchSubmit(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    handleKeywordFilterChange(searchDraft.trim());
  }

  function handleSearchClear() {
    setSearchDraft('');
    handleKeywordFilterChange('');
  }

  function handleResetFilters() {
    setSearchDraft('');
    setKeywordFilter('');
    setReviewStatusFilter('');
    setAIStatusFilter('');
    setContentKindFilter('');
    setDeliverableStatusFilter('');
    setThinkTankFilter('');
    setSourceFilter('');
    resetReportListSelection();
  }

  function handleThinkTankFilterChange(value: number | '') {
    setThinkTankFilter(value);
    setSourceFilter('');
    resetReportListSelection();
  }

  function handleSourceFilterChange(value: number | '') {
    setSourceFilter(value);
    resetReportListSelection();
  }

  function handleWorkflowShortcut(value: ReportWorkflowShortcut) {
    setPage(1);
    resetReportListState();
    setSearchDraft('');
    setKeywordFilter('');
    setContentKindFilter('');
    setDeliverableStatusFilter('');
    setThinkTankFilter('');
    setSourceFilter('');

    if (value === 'teacher_review') {
      setReviewStatusFilter('pending_review');
      setAIStatusFilter('success');
      setDeliverableStatusFilter('complete');
      return;
    }

    if (value === 'ready_export') {
      setReviewStatusFilter('');
      setAIStatusFilter('success');
      setDeliverableStatusFilter('complete');
      return;
    }

    if (value === 'needs_rerun') {
      setReviewStatusFilter('needs_rerun');
      setAIStatusFilter('');
      return;
    }

    setReviewStatusFilter('');
    setAIStatusFilter('');
  }

  return {
    page,
    setPage,
    reviewStatusFilter,
    aiStatusFilter,
    contentKindFilter,
    deliverableStatusFilter,
    searchDraft,
    keywordFilter,
    thinkTankFilter,
    sourceFilter,
    setSearchDraft,
    handleReviewStatusFilterChange,
    handleAIStatusFilterChange,
    handleContentKindFilterChange,
    handleDeliverableStatusFilterChange,
    handleSearchSubmit,
    handleSearchClear,
    handleResetFilters,
    handleThinkTankFilterChange,
    handleSourceFilterChange,
    handleWorkflowShortcut,
  };
}
