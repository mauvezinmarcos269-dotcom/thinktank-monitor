'use client';

import { useState } from 'react';

import {
  downloadCrawlCandidatesCsv,
  fetchCrawlCandidateStatistics,
  fetchCrawlCandidates,
  type CrawlCandidate,
  type CrawlCandidateStatistics,
} from '@/lib/institution';

import { type CandidateFilters } from './candidate-detail';
import { candidatePageSize } from './settings-page-utils';

type UseCandidateDetailsParams = {
  setErrorMessage: (message: string | null) => void;
};

export function useCandidateDetails({
  setErrorMessage,
}: UseCandidateDetailsParams) {
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

    await applyCandidateFilters(crawlRunId, next);
  }

  async function applyCandidateFilters(
    crawlRunId: number,
    filters: CandidateFilters
  ) {
    setCandidateFiltersByRunId((current) => ({
      ...current,
      [crawlRunId]: filters,
    }));
    setCandidateLoadingRunId(crawlRunId);
    setErrorMessage(null);

    try {
      const response = await fetchCrawlCandidates({
        crawlRunId,
        skip: 0,
        limit: candidatePageSize,
        status: filters.status,
        skipReasonLabel: filters.reason,
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

  return {
    expandedRunId,
    candidateLoadingRunId,
    candidateExportingRunId,
    candidatesByRunId,
    candidateTotalByRunId,
    candidateStatisticsByRunId,
    candidateFiltersByRunId,
    handleToggleCandidates,
    handleLoadMoreCandidates,
    updateCandidateFilter,
    applyCandidateFilters,
    handleExportCandidates,
  };
}
