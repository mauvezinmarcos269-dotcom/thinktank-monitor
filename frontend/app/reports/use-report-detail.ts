'use client';

import {
  type Dispatch,
  type SetStateAction,
  useCallback,
  useEffect,
  useState,
} from 'react';
import { useSearchParams } from 'next/navigation';

import {
  fetchAIProgress,
  fetchReport,
  fetchReportReviewEvents,
  retryReportAI,
  triggerFetchContent,
  type AIProgress,
  type Report,
  type ReportReviewEvent,
} from '@/lib/report';

import {
  getPreferredReportView,
  type ReportView,
} from './report-page-utils';

type UseReportDetailParams = {
  setReports: Dispatch<SetStateAction<Report[]>>;
  setSelectedReportIds: Dispatch<SetStateAction<Set<number>>>;
  setTaskMessage: Dispatch<SetStateAction<string | null>>;
};

export function useReportDetail({
  setReports,
  setSelectedReportIds,
  setTaskMessage,
}: UseReportDetailParams) {
  const searchParams = useSearchParams();
  const [selected, setSelected] = useState<Report | null>(null);
  const [aiProgress, setAIProgress] = useState<AIProgress | null>(null);
  const [reviewEvents, setReviewEvents] = useState<ReportReviewEvent[]>([]);
  const [activeView, setActiveView] = useState<ReportView>('content');
  const [reviewNoteDraft, setReviewNoteDraft] = useState('');

  const [detailError, setDetailError] = useState<string | null>(null);
  const [progressError, setProgressError] = useState<string | null>(null);
  const [reviewEventsError, setReviewEventsError] = useState<string | null>(
    null
  );

  const [loadingDetail, setLoadingDetail] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(false);
  const [loadingReviewEvents, setLoadingReviewEvents] = useState(false);
  const [submittingFetch, setSubmittingFetch] = useState(false);
  const [submittingAIReportId, setSubmittingAIReportId] = useState<
    number | null
  >(null);

  const loadAIProgress = useCallback(async (reportId: number) => {
    setLoadingProgress(true);
    setProgressError(null);

    try {
      const progress = await fetchAIProgress(reportId);
      setAIProgress(progress);
    } catch (err) {
      setAIProgress(null);
      setProgressError((err as Error).message);
    } finally {
      setLoadingProgress(false);
    }
  }, []);

  const loadReviewEvents = useCallback(async (reportId: number) => {
    setLoadingReviewEvents(true);
    setReviewEventsError(null);

    try {
      const events = await fetchReportReviewEvents(reportId);
      setReviewEvents(events);
    } catch (err) {
      setReviewEvents([]);
      setReviewEventsError((err as Error).message);
    } finally {
      setLoadingReviewEvents(false);
    }
  }, []);

  const handleSelect = useCallback(async (reportId: number) => {
    setLoadingDetail(true);
    setDetailError(null);
    setProgressError(null);
    setTaskMessage(null);

    try {
      const report = await fetchReport(reportId);
      setSelected(report);
      setReports((current) => {
        const exists = current.some((item) => item.id === report.id);
        return exists
          ? current.map((item) => (item.id === report.id ? report : item))
          : [report, ...current];
      });
      setActiveView(getPreferredReportView(report, searchParams.get('view')));
      await loadAIProgress(report.id);
      await loadReviewEvents(report.id);
    } catch (err) {
      setDetailError((err as Error).message);
    } finally {
      setLoadingDetail(false);
    }
  }, [loadAIProgress, loadReviewEvents, searchParams, setReports, setTaskMessage]);

  async function handleFetchContent() {
    if (!selected) {
      return;
    }

    setSubmittingFetch(true);
    setDetailError(null);
    setTaskMessage(null);

    try {
      const response = await triggerFetchContent(selected.id);

      setTaskMessage(
        `${response.message} 任务 ID：${response.task_id ?? '无'}`
      );

      setSelected((current) =>
        current
          ? {
              ...current,
              crawl_status: response.crawl_status,
              crawl_error: null,
              updated_at: response.updated_at,
            }
          : null
      );
    } catch (err) {
      setDetailError((err as Error).message);
    } finally {
      setSubmittingFetch(false);
    }
  }

  async function submitRetryAI(reportId: number) {
    setSubmittingAIReportId(reportId);
    setDetailError(null);
    setProgressError(null);
    setTaskMessage(null);

    try {
      const response = await retryReportAI(reportId);
      const reviewStatus = response.review_status ?? 'pending_review';

      setTaskMessage(
        `${response.message} 任务 ID：${response.task_id ?? '无'}`
      );

      setReports((current) =>
        current.map((report) =>
          report.id === reportId
            ? {
                ...report,
                ai_status: response.ai_status,
                review_status: reviewStatus,
                updated_at: response.updated_at,
              }
            : report
        )
      );

      setSelected((current) =>
        current && current.id === reportId
          ? {
              ...current,
              ai_status: response.ai_status,
              review_status: reviewStatus,
              updated_at: response.updated_at,
            }
          : current
      );

      if (selected?.id === reportId) {
        await loadAIProgress(reportId);
        await loadReviewEvents(reportId);
      }
    } catch (err) {
      setDetailError((err as Error).message);
    } finally {
      setSubmittingAIReportId(null);
    }
  }

  async function handleRetryAI() {
    if (!selected) {
      return;
    }

    await submitRetryAI(selected.id);
  }

  function resetReportListState() {
    setSelected(null);
    setAIProgress(null);
    setReviewEvents([]);
    setSelectedReportIds(new Set());
  }

  useEffect(() => {
    setReviewNoteDraft(selected?.review_note ?? '');
  }, [selected]);

  return {
    selected,
    setSelected,
    aiProgress,
    reviewEvents,
    activeView,
    setActiveView,
    reviewNoteDraft,
    setReviewNoteDraft,
    detailError,
    setDetailError,
    progressError,
    reviewEventsError,
    loadingDetail,
    loadingProgress,
    loadingReviewEvents,
    submittingFetch,
    submittingAIReportId,
    loadReviewEvents,
    handleSelect,
    handleFetchContent,
    submitRetryAI,
    handleRetryAI,
    resetReportListState,
  };
}
