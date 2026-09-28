'use client';

import {
  type Dispatch,
  type SetStateAction,
  useEffect,
  useState,
} from 'react';

import {
  fetchReports,
  type Report,
} from '@/lib/report';
import {
  type ReportAIStatus,
  type ReportContentKind,
  type ReportDeliverableStatus,
  type ReportReviewStatus,
} from '@/lib/status';

import { PAGE_SIZE } from './report-page-utils';

type UseReportListParams = {
  page: number;
  reviewStatusFilter: ReportReviewStatus | '';
  aiStatusFilter: ReportAIStatus | '';
  contentKindFilter: ReportContentKind | '';
  deliverableStatusFilter: ReportDeliverableStatus | '';
  keywordFilter: string;
  thinkTankFilter: number | '';
  sourceFilter: number | '';
  focusedReportId: number;
  setReports: Dispatch<SetStateAction<Report[]>>;
  setListError: Dispatch<SetStateAction<string | null>>;
  setSelectedReportIds: Dispatch<SetStateAction<Set<number>>>;
  handleSelect: (reportId: number) => Promise<void>;
};

export function useReportList({
  page,
  reviewStatusFilter,
  aiStatusFilter,
  contentKindFilter,
  deliverableStatusFilter,
  keywordFilter,
  thinkTankFilter,
  sourceFilter,
  focusedReportId,
  setReports,
  setListError,
  setSelectedReportIds,
  handleSelect,
}: UseReportListParams) {
  const [totalReports, setTotalReports] = useState(0);
  const [loadingList, setLoadingList] = useState(true);

  useEffect(() => {
    setLoadingList(true);
    setListError(null);

    fetchReports({
      skip: (page - 1) * PAGE_SIZE,
      limit: PAGE_SIZE,
      reviewStatus: reviewStatusFilter,
      aiStatus: aiStatusFilter,
      contentKind: contentKindFilter,
      deliverableStatus: deliverableStatusFilter,
      keyword: keywordFilter,
      thinkTankId: thinkTankFilter,
      sourceId: sourceFilter,
    })
      .then((data) => {
        setReports(data.items);
        setTotalReports(data.total);
        setSelectedReportIds(new Set());

        if (focusedReportId) {
          handleSelect(focusedReportId);
        } else if (data.items.length > 0) {
          handleSelect(data.items[0].id);
        }
      })
      .catch((err: Error) => setListError(err.message))
      .finally(() => setLoadingList(false));
  }, [
    page,
    reviewStatusFilter,
    aiStatusFilter,
    contentKindFilter,
    deliverableStatusFilter,
    keywordFilter,
    thinkTankFilter,
    sourceFilter,
    focusedReportId,
    setReports,
    setListError,
    setSelectedReportIds,
    handleSelect,
  ]);

  return {
    totalReports,
    loadingList,
  };
}
