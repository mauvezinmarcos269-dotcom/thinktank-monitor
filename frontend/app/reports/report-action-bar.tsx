'use client';

import { type Report } from '@/lib/report';
import { reportAIStatusLabels } from '@/lib/status';

import {
  countTextChars,
  isAIProcessing,
  type CopyTarget,
} from './report-page-utils';

type ReportActionBarProps = {
  report: Report;
  canFetchContent: boolean;
  canRetryAI: boolean;
  submittingFetch: boolean;
  submittingAIReportId: number | null;
  exportingReport: boolean;
  exportingDocx: boolean;
  copyingTarget: CopyTarget | null;
  aiActionLabel: string;
  onFetchContent: () => void;
  onRetryAI: () => void;
  onExportMarkdown: () => void;
  onExportDocx: () => void;
  onCopyCommentary: () => void;
  onCopyTranslation: () => void;
};

export function ReportActionBar({
  report,
  canFetchContent,
  canRetryAI,
  submittingFetch,
  submittingAIReportId,
  exportingReport,
  exportingDocx,
  copyingTarget,
  aiActionLabel,
  onFetchContent,
  onRetryAI,
  onExportMarkdown,
  onExportDocx,
  onCopyCommentary,
  onCopyTranslation,
}: ReportActionBarProps) {
  const hasCommentaryText =
    countTextChars(report.summary) > 0 || countTextChars(report.commentary) > 0;
  const hasTranslationText = countTextChars(report.translation) > 0;
  const hasDeliverable = hasCommentaryText || hasTranslationText;
  const hasContentText = countTextChars(report.content) > 0;
  const isFetchingContent = submittingFetch || report.crawl_status === 'running';
  const fetchContentLabel = submittingFetch
    ? '正在提交抓取任务……'
    : report.crawl_status === 'running'
      ? '正在抓取正文……'
      : '抓取正文';
  const isSubmittingCurrentAI = submittingAIReportId === report.id;
  const isCurrentAIProcessing = isAIProcessing(report);
  const retryAIButtonLabel = isSubmittingCurrentAI
    ? '正在提交 AI 任务……'
    : isCurrentAIProcessing
      ? (reportAIStatusLabels[report.ai_status] ?? report.ai_status)
      : aiActionLabel;

  return (
    <div className="report-action-groups">
      {(canFetchContent || (canRetryAI && hasContentText)) && (
        <section className="action-group action-group-maintenance">
          <div>
            <h4>维护操作</h4>
            <p>用于重新抓取正文或重新生成 AI 成果。</p>
          </div>

          <div className="action-row report-primary-actions">
            {canFetchContent && (
              <button
                type="button"
                onClick={onFetchContent}
                disabled={isFetchingContent}
              >
                {fetchContentLabel}
              </button>
            )}

            {canRetryAI && hasContentText && (
              <button
                type="button"
                onClick={onRetryAI}
                disabled={isSubmittingCurrentAI || isCurrentAIProcessing}
              >
                {retryAIButtonLabel}
              </button>
            )}
          </div>
        </section>
      )}

      <section className="action-group">
        <div>
          <h4>备用成果操作</h4>
          <p>主成果区已有快捷导出，这里保留同一报告的备用复制与导出入口。</p>
        </div>

        <div className="action-row">
          <button
            type="button"
            onClick={onExportDocx}
            disabled={exportingDocx || !hasDeliverable}
          >
            {exportingDocx ? '正在导出 Word……' : '导出成果 Word'}
          </button>

          <button
            type="button"
            onClick={onExportMarkdown}
            disabled={exportingReport || !hasDeliverable}
          >
            {exportingReport ? '正在导出……' : '导出成果 Markdown'}
          </button>
        </div>

        <div className="action-row">
          <button
            type="button"
            onClick={onCopyCommentary}
            disabled={copyingTarget !== null || !hasCommentaryText}
          >
            {copyingTarget === 'commentary' ? '正在复制……' : '复制评论稿'}
          </button>
          <button
            type="button"
            onClick={onCopyTranslation}
            disabled={copyingTarget !== null || !hasTranslationText}
          >
            {copyingTarget === 'translation' ? '正在复制……' : '复制全文翻译'}
          </button>
        </div>
      </section>
    </div>
  );
}
