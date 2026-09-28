'use client';

import { type Source, type ThinkTank } from '@/lib/institution';
import { type Report } from '@/lib/report';

import { ReportListItem } from './report-list-item';

type ReportListProps = {
  reports: Report[];
  sourcesById: Map<number, Source>;
  thinkTanksById: Map<number, ThinkTank>;
  selectedReportIds: Set<number>;
  activeReportId: number | null;
  canRetryAI: boolean;
  selectionDisabled: boolean;
  submittingAIReportId: number | null;
  onSelectReport: (reportId: number) => void;
  onToggleReportSelection: (reportId: number) => void;
  onRetryAI: (reportId: number) => void;
  onResetFilters: () => void;
};

export function ReportList({
  reports,
  sourcesById,
  thinkTanksById,
  selectedReportIds,
  activeReportId,
  canRetryAI,
  selectionDisabled,
  submittingAIReportId,
  onSelectReport,
  onToggleReportSelection,
  onRetryAI,
  onResetFilters,
}: ReportListProps) {
  if (reports.length === 0) {
    return (
      <div className="empty-state">
        <strong>暂无匹配报告</strong>
        <p>可以切换上方快捷筛选，或清空关键词后重新查看全部报告。</p>
        <button type="button" onClick={onResetFilters}>
          重置筛选
        </button>
      </div>
    );
  }

  return (
    <ul className="report-list">
      {reports.map((report) => {
        const source = sourcesById.get(report.source_id);
        const thinkTank = source
          ? thinkTanksById.get(source.think_tank_id) ?? null
          : null;

        return (
          <ReportListItem
            key={report.id}
            report={report}
            source={source}
            thinkTank={thinkTank}
            selected={selectedReportIds.has(report.id)}
            active={activeReportId === report.id}
            canRetryAI={canRetryAI}
            selectionDisabled={selectionDisabled}
            submittingAIReportId={submittingAIReportId}
            onSelectReport={onSelectReport}
            onToggleReportSelection={onToggleReportSelection}
            onRetryAI={onRetryAI}
          />
        );
      })}
    </ul>
  );
}
