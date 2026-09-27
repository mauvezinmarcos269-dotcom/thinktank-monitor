'use client';

import { type RefObject } from 'react';

import { type Source, type ThinkTank } from '@/lib/institution';
import {
  type AIProgress,
  type Report,
  type ReportReviewEvent,
} from '@/lib/report';

import { AIProgressPanel } from './ai-progress-panel';
import { ReportActionBar } from './report-action-bar';
import { ReportContentViewer } from './report-content-viewer';
import {
  ReportDetailHeader,
  type ReportDocumentType,
} from './report-detail-header';
import { ReportMetadataGrid } from './report-metadata-grid';
import { ReportOutcomeSummary } from './report-outcome-summary';
import {
  type CopyTarget,
  type ReportView,
} from './report-page-utils';
import { ReportReadingBrief } from './report-reading-brief';
import { ReviewHistoryPanel } from './review-history-panel';

type ReportDetailArticleProps = {
  report: Report;
  documentType: ReportDocumentType;
  source: Source | null;
  thinkTank: ThinkTank | null;
  activeView: ReportView;
  copyingTarget: CopyTarget | null;
  exportingReport: boolean;
  exportingDocx: boolean;
  canFetchContent: boolean;
  canRetryAI: boolean;
  submittingFetch: boolean;
  submittingAIReportId: number | null;
  aiActionLabel: string;
  updatingReview: boolean;
  reviewNoteDraft: string;
  highlightReviewSection: boolean;
  reviewSectionRef: RefObject<HTMLDivElement | null>;
  adminDetailsSummary: string;
  reviewHistorySummary: string;
  aiProgressSummary: string;
  loadingReviewEvents: boolean;
  reviewEventsError: string | null;
  reviewEvents: ReportReviewEvent[];
  loadingProgress: boolean;
  progressError: string | null;
  aiProgress: AIProgress | null;
  openReviewDetails: boolean;
  onViewSelect: (view: ReportView) => void;
  onCopyCommentary: () => void;
  onCopyTranslation: () => void;
  onCopyCurrent: () => void;
  onExportMarkdown: () => void;
  onExportDocx: () => void;
  onReviewStatusChange: Parameters<typeof ReportMetadataGrid>[0]['onReviewStatusChange'];
  onReviewNoteChange: (value: string) => void;
  onReviewNoteSave: () => void;
  onFetchContent: () => void;
  onRetryAI: () => void;
};

export function ReportDetailArticle({
  report,
  documentType,
  source,
  thinkTank,
  activeView,
  copyingTarget,
  exportingReport,
  exportingDocx,
  canFetchContent,
  canRetryAI,
  submittingFetch,
  submittingAIReportId,
  aiActionLabel,
  updatingReview,
  reviewNoteDraft,
  highlightReviewSection,
  reviewSectionRef,
  adminDetailsSummary,
  reviewHistorySummary,
  aiProgressSummary,
  loadingReviewEvents,
  reviewEventsError,
  reviewEvents,
  loadingProgress,
  progressError,
  aiProgress,
  openReviewDetails,
  onViewSelect,
  onCopyCommentary,
  onCopyTranslation,
  onCopyCurrent,
  onExportMarkdown,
  onExportDocx,
  onReviewStatusChange,
  onReviewNoteChange,
  onReviewNoteSave,
  onFetchContent,
  onRetryAI,
}: ReportDetailArticleProps) {
  return (
    <article className="report-detail">
      <ReportDetailHeader
        report={report}
        documentType={documentType}
        source={source}
        thinkTank={thinkTank}
      />

      <ReportReadingBrief report={report} onViewSelect={onViewSelect} />

      <ReportOutcomeSummary
        report={report}
        activeView={activeView}
        copyingTarget={copyingTarget}
        exportingReport={exportingReport}
        exportingDocx={exportingDocx}
        onViewSelect={onViewSelect}
        onCopyCommentary={onCopyCommentary}
        onCopyTranslation={onCopyTranslation}
        onExportMarkdown={onExportMarkdown}
        onExportDocx={onExportDocx}
      />

      {report.crawl_error ? (
        <p className="message-error">抓取错误：{report.crawl_error}</p>
      ) : null}

      <ReportContentViewer
        report={report}
        activeView={activeView}
        copyingTarget={copyingTarget}
        onActiveViewChange={onViewSelect}
        onCopyCurrent={onCopyCurrent}
      />

      <section className="secondary-detail-group">
        <details className="secondary-details" open={openReviewDetails}>
          <summary>
            <span>文档信息、复核与导出操作</span>
            <small>{adminDetailsSummary}</small>
          </summary>
          <ReportMetadataGrid
            report={report}
            documentType={documentType}
            source={source}
            thinkTank={thinkTank}
            canReview={canRetryAI}
            updatingReview={updatingReview}
            reviewNoteDraft={reviewNoteDraft}
            highlightReviewSection={highlightReviewSection}
            reviewSectionRef={reviewSectionRef}
            onReviewStatusChange={onReviewStatusChange}
            onReviewNoteChange={onReviewNoteChange}
            onReviewNoteSave={onReviewNoteSave}
          />

          <ReportActionBar
            report={report}
            canFetchContent={canFetchContent}
            canRetryAI={canRetryAI}
            submittingFetch={submittingFetch}
            submittingAIReportId={submittingAIReportId}
            exportingReport={exportingReport}
            exportingDocx={exportingDocx}
            copyingTarget={copyingTarget}
            aiActionLabel={aiActionLabel}
            onFetchContent={onFetchContent}
            onRetryAI={onRetryAI}
            onExportMarkdown={onExportMarkdown}
            onExportDocx={onExportDocx}
            onCopyCommentary={onCopyCommentary}
            onCopyTranslation={onCopyTranslation}
          />
        </details>

        <details className="secondary-details">
          <summary>
            <span>复核历史</span>
            <small>{reviewHistorySummary}</small>
          </summary>
          <ReviewHistoryPanel
            loading={loadingReviewEvents}
            errorMessage={reviewEventsError}
            events={reviewEvents}
          />
        </details>

        <details className="secondary-details">
          <summary>
            <span>AI 分块进度</span>
            <small>{aiProgressSummary}</small>
          </summary>
          <AIProgressPanel
            loading={loadingProgress}
            errorMessage={progressError}
            progress={aiProgress}
          />
        </details>
      </section>
    </article>
  );
}
