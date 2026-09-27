'use client';

import { type Report } from '@/lib/report';

import {
  countTextChars,
  getReportWorkflowState,
  type CopyTarget,
  type ReportView,
} from './report-page-utils';

type OutcomeItem = {
  label: string;
  count: number;
  view: ReportView;
};

type ReportOutcomeSummaryProps = {
  report: Report;
  activeView: ReportView;
  copyingTarget: CopyTarget | null;
  exportingReport: boolean;
  exportingDocx: boolean;
  onViewSelect: (view: ReportView) => void;
  onCopyCommentary: () => void;
  onCopyTranslation: () => void;
  onExportMarkdown: () => void;
  onExportDocx: () => void;
};

function getOutcomeStatus(item: OutcomeItem): string {
  return item.count > 0 ? `已生成 ${item.count} 字` : '尚未生成';
}

function getOutcomeCardClass(item: OutcomeItem, activeView: ReportView): string {
  if (activeView === item.view) {
    return 'outcome-card outcome-card-active';
  }

  if (item.count > 0) {
    return 'outcome-card outcome-card-ready';
  }

  return 'outcome-card outcome-card-empty';
}

function getOutcomeBadge(item: OutcomeItem, activeView: ReportView): string {
  if (activeView === item.view) {
    return '当前阅读';
  }

  return item.count > 0 ? '可阅读' : '待生成';
}

function getRecommendedView(outcomes: OutcomeItem[]): ReportView | null {
  return (
    outcomes.find((item) => item.view === 'summary' && item.count > 0)?.view ??
    outcomes.find((item) => item.view === 'commentary' && item.count > 0)?.view ??
    outcomes.find((item) => item.count > 0)?.view ??
    null
  );
}

export function ReportOutcomeSummary({
  report,
  activeView,
  copyingTarget,
  exportingReport,
  exportingDocx,
  onViewSelect,
  onCopyCommentary,
  onCopyTranslation,
  onExportMarkdown,
  onExportDocx,
}: ReportOutcomeSummaryProps) {
  const workflow = getReportWorkflowState(report);
  const outcomes: OutcomeItem[] = [
    {
      label: '主要观点',
      count: countTextChars(report.summary),
      view: 'summary',
    },
    {
      label: '深层研判',
      count: countTextChars(report.commentary),
      view: 'commentary',
    },
    {
      label: '全文翻译',
      count: countTextChars(report.translation),
      view: 'translation',
    },
  ];
  const hasDeliverable = outcomes.some((item) => item.count > 0);
  const hasCommentaryText =
    countTextChars(report.summary) > 0 || countTextChars(report.commentary) > 0;
  const hasTranslationText = countTextChars(report.translation) > 0;
  const recommendedView = getRecommendedView(outcomes);
  const completedCount = outcomes.filter((item) => item.count > 0).length;

  return (
    <section className="outcome-summary" aria-label="成果概览">
      <div className="outcome-summary-main">
        <div className="outcome-summary-status">
          <span className={workflow.className}>{workflow.label}</span>
          <span className="badge badge-info">成果 {completedCount}/3</span>
        </div>
        <h3>AI 成果工作台</h3>
        <p>{workflow.hint}</p>
        <div className="outcome-primary-actions">
          {recommendedView ? (
            <button
              type="button"
              onClick={() => onViewSelect(recommendedView)}
              disabled={activeView === recommendedView}
            >
              {activeView === recommendedView ? '正在阅读推荐内容' : '阅读推荐内容'}
            </button>
          ) : null}
          <button
            type="button"
            onClick={onCopyCommentary}
            disabled={copyingTarget !== null || !hasCommentaryText}
          >
            {copyingTarget === 'commentary' ? '正在复制……' : '复制评论稿'}
          </button>
        </div>
        <div className="outcome-secondary-actions">
          <button
            type="button"
            onClick={onExportDocx}
            disabled={exportingDocx || !hasDeliverable}
          >
            {exportingDocx ? '正在导出 Word……' : '导出 Word'}
          </button>
          <button
            type="button"
            onClick={onExportMarkdown}
            disabled={exportingReport || !hasDeliverable}
          >
            {exportingReport ? '正在导出……' : '导出 Markdown'}
          </button>
          <button
            type="button"
            onClick={onCopyTranslation}
            disabled={copyingTarget !== null || !hasTranslationText}
          >
            {copyingTarget === 'translation' ? '正在复制……' : '复制全文翻译'}
          </button>
        </div>
      </div>
      <dl className="outcome-summary-grid">
        {outcomes.map((item) => (
          <div key={item.label} className={getOutcomeCardClass(item, activeView)}>
            <dt>
              <span>{item.label}</span>
              <small>{getOutcomeBadge(item, activeView)}</small>
            </dt>
            <dd>{getOutcomeStatus(item)}</dd>
            <button
              type="button"
              onClick={() => onViewSelect(item.view)}
              disabled={item.count === 0 || activeView === item.view}
            >
              {activeView === item.view ? '正在阅读' : `阅读${item.label}`}
            </button>
          </div>
        ))}
      </dl>
    </section>
  );
}
