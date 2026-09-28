'use client';

import { type RefObject } from 'react';

import { type Source, type ThinkTank } from '@/lib/institution';
import {
  type AIProgress,
  type Report,
  type ReportReviewEvent,
} from '@/lib/report';

import { ReportDetailArticle } from './report-detail-article';
import { type ReportDocumentType } from './report-detail-header';
import {
  type CopyTarget,
  type ReportView,
} from './report-page-utils';
import { type ReportReviewStatus } from '@/lib/status';

type ReportDetailPanelProps = {
  selected: Report | null;
  selectedDocumentType: ReportDocumentType | null;
  selectedSource: Source | null;
  selectedThinkTank: ThinkTank | null;
  loadingDetail: boolean;
  detailError: string | null;
  taskMessage: string | null;
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
  onReviewStatusChange: (value: ReportReviewStatus) => void;
  onReviewNoteChange: (value: string) => void;
  onReviewNoteSave: () => void;
  onFetchContent: () => void;
  onRetryAI: () => void;
};

export function ReportDetailPanel({
  selected,
  selectedDocumentType,
  selectedSource,
  selectedThinkTank,
  loadingDetail,
  detailError,
  taskMessage,
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
}: ReportDetailPanelProps) {
  return (
    <section className="panel report-detail-panel">
      {loadingDetail && <p>正在加载报告详情……</p>}
      {detailError && (
        <p className="message-error">{detailError}</p>
      )}
      {taskMessage && (
        <p className="message-success">{taskMessage}</p>
      )}

      {selected && selectedDocumentType && !loadingDetail && (
        <ReportDetailArticle
          report={selected}
          documentType={selectedDocumentType}
          source={selectedSource}
          thinkTank={selectedThinkTank}
          activeView={activeView}
          copyingTarget={copyingTarget}
          exportingReport={exportingReport}
          exportingDocx={exportingDocx}
          canFetchContent={canFetchContent}
          canRetryAI={canRetryAI}
          submittingFetch={submittingFetch}
          submittingAIReportId={submittingAIReportId}
          aiActionLabel={aiActionLabel}
          updatingReview={updatingReview}
          reviewNoteDraft={reviewNoteDraft}
          highlightReviewSection={highlightReviewSection}
          reviewSectionRef={reviewSectionRef}
          adminDetailsSummary={adminDetailsSummary}
          reviewHistorySummary={reviewHistorySummary}
          aiProgressSummary={aiProgressSummary}
          loadingReviewEvents={loadingReviewEvents}
          reviewEventsError={reviewEventsError}
          reviewEvents={reviewEvents}
          loadingProgress={loadingProgress}
          progressError={progressError}
          aiProgress={aiProgress}
          openReviewDetails={openReviewDetails}
          onViewSelect={onViewSelect}
          onCopyCommentary={onCopyCommentary}
          onCopyTranslation={onCopyTranslation}
          onCopyCurrent={onCopyCurrent}
          onExportMarkdown={onExportMarkdown}
          onExportDocx={onExportDocx}
          onReviewStatusChange={onReviewStatusChange}
          onReviewNoteChange={onReviewNoteChange}
          onReviewNoteSave={onReviewNoteSave}
          onFetchContent={onFetchContent}
          onRetryAI={onRetryAI}
        />
      )}

      {!selected && !loadingDetail && !detailError && (
        <div className="empty-state empty-state-large">
          <strong>请选择一篇报告</strong>
          <p>
            从左侧列表选择报告后，这里会显示全文翻译、主要观点和深层研判。
          </p>
        </div>
      )}
    </section>
  );
}
