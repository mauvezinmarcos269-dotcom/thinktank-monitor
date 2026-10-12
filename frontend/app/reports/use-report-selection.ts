'use client';

import { useMemo, useState } from 'react';

import { type Report } from '@/lib/report';

export function useReportSelection(reports: Report[]) {
  const [selectedReportIds, setSelectedReportIds] = useState<Set<number>>(
    () => new Set()
  );
  const visibleReportIds = useMemo(
    () => reports.map((report) => report.id),
    [reports]
  );
  const visibleSelectedReportCount = visibleReportIds.filter((reportId) =>
    selectedReportIds.has(reportId)
  ).length;
  const allVisibleSelected =
    visibleReportIds.length > 0 &&
    visibleSelectedReportCount === visibleReportIds.length;

  function toggleReportSelection(reportId: number) {
    setSelectedReportIds((current) => {
      const next = new Set(current);
      if (next.has(reportId)) {
        next.delete(reportId);
      } else {
        next.add(reportId);
      }
      return next;
    });
  }

  function toggleAllVisibleReports() {
    setSelectedReportIds((current) => {
      const next = new Set(current);
      if (allVisibleSelected) {
        visibleReportIds.forEach((reportId) => next.delete(reportId));
      } else {
        visibleReportIds.forEach((reportId) => next.add(reportId));
      }
      return next;
    });
  }

  function clearReportSelection() {
    setSelectedReportIds(new Set());
  }

  return {
    selectedReportIds,
    setSelectedReportIds,
    visibleSelectedReportCount,
    allVisibleSelected,
    toggleReportSelection,
    toggleAllVisibleReports,
    clearReportSelection,
  };
}
