'use client';

import { type RefObject } from 'react';

import { type Source, type ThinkTank } from '@/lib/institution';
import { type Report } from '@/lib/report';
import {
  priorityTierLabels,
  reportAIStatusLabels,
  reportCrawlStatusLabels,
  reportReviewStatusLabels,
  sourceCrawlStatusLabels,
  sourceTypeLabels,
  type ReportReviewStatus,
} from '@/lib/status';

import {
  countTextChars,
  reviewStatusOptions,
} from './report-page-utils';
import { type ReportDocumentType } from './report-detail-header';

const reviewQuickActions: Array<{
  status: ReportReviewStatus;
  label: string;
  hint: string;
}> = [
  {
    status: 'approved',
    label: '通过',
    hint: '成果可交付',
  },
  {
    status: 'needs_rerun',
    label: '需重跑',
    hint: '先写明原因',
  },
  {
    status: 'rejected',
    label: '不采用',
    hint: '保留处理记录',
  },
];

type ReportMetadataGridProps = {
  report: Report;
  documentType: ReportDocumentType;
  source: Source | null;
  thinkTank: ThinkTank | null;
  canReview: boolean;
  updatingReview: boolean;
  reviewNoteDraft: string;
  highlightReviewSection: boolean;
  reviewSectionRef: RefObject<HTMLDivElement | null>;
  onReviewStatusChange: (value: ReportReviewStatus) => void;
  onReviewNoteChange: (value: string) => void;
  onReviewNoteSave: () => void;
};

export function ReportMetadataGrid({
  report,
  documentType,
  source,
  thinkTank,
  canReview,
  updatingReview,
  reviewNoteDraft,
  highlightReviewSection,
  reviewSectionRef,
  onReviewStatusChange,
  onReviewNoteChange,
  onReviewNoteSave,
}: ReportMetadataGridProps) {
  const reviewFocusClass = highlightReviewSection
    ? 'review-focus-card review-focus-card-active'
    : 'review-focus-card';
  const reviewNoteClass = highlightReviewSection
    ? 'review-note-editor review-focus-card-active'
    : 'review-note-editor';

  return (
    <div className="report-detail-admin">
      <section ref={reviewSectionRef} className={reviewFocusClass}>
        <div>
          <h4>复核处理</h4>
          <p>确认本篇报告是否可进入正式成果，或记录需重跑、不采用的原因。</p>
        </div>

        {canReview ? (
          <div className="review-quick-actions" aria-label="复核快捷操作">
            {reviewQuickActions.map((action) => (
              <button
                key={action.status}
                type="button"
                className={
                  report.review_status === action.status
                    ? 'review-quick-action-active'
                    : undefined
                }
                onClick={() => onReviewStatusChange(action.status)}
                disabled={updatingReview}
              >
                <span>{action.label}</span>
                <small>{action.hint}</small>
              </button>
            ))}
          </div>
        ) : null}

        <div className="review-control-grid">
          <label>
            <span>复核状态</span>
            {canReview ? (
              <select
                value={report.review_status}
                onChange={(event) =>
                  onReviewStatusChange(event.target.value as ReportReviewStatus)
                }
                disabled={updatingReview}
              >
                {reviewStatusOptions.map((status) => (
                  <option key={status} value={status}>
                    {reportReviewStatusLabels[status]}
                  </option>
                ))}
              </select>
            ) : (
              <strong>
                {reportReviewStatusLabels[report.review_status] ??
                  report.review_status}
              </strong>
            )}
          </label>

          <label className={reviewNoteClass}>
            <span>复核意见</span>
            {canReview ? (
              <textarea
                value={reviewNoteDraft}
                onChange={(event) => onReviewNoteChange(event.target.value)}
                maxLength={4000}
                rows={4}
                disabled={updatingReview}
                placeholder="记录需重跑原因、不采用理由或已通过说明"
              />
            ) : (
              <strong>{report.review_note || '暂无'}</strong>
            )}
            {canReview ? (
              <small>{reviewNoteDraft.trim().length} / 4000 字</small>
            ) : null}
          </label>
        </div>

        {canReview && (
          <button
            type="button"
            onClick={onReviewNoteSave}
            disabled={
              updatingReview || reviewNoteDraft === (report.review_note ?? '')
            }
          >
            保存意见
          </button>
        )}
      </section>

      <section>
        <h4>文档信息</h4>
        <dl className="metadata-grid">
          <div>
            <dt>智库机构</dt>
            <dd>{thinkTank?.name ?? '未知'}</dd>
          </div>

          <div>
            <dt>国家/地区</dt>
            <dd>{thinkTank?.country ?? '未知'}</dd>
          </div>

          <div>
            <dt>优先级</dt>
            <dd>
              {thinkTank
                ? priorityTierLabels[thinkTank.priority_tier] ??
                  thinkTank.priority_tier
                : '未知'}
            </dd>
          </div>

          <div>
            <dt>来源类型</dt>
            <dd>
              {source
                ? sourceTypeLabels[source.source_type] ?? source.source_type
                : '未知'}
            </dd>
          </div>

          <div className="metadata-wide">
            <dt>来源 URL</dt>
            <dd>
              {source ? (
                <a href={source.url} target="_blank" rel="noreferrer">
                  {source.url}
                </a>
              ) : (
                '未知'
              )}
            </dd>
          </div>

          <div>
            <dt>来源状态</dt>
            <dd>
              {source
                ? sourceCrawlStatusLabels[source.last_crawl_status] ??
                  source.last_crawl_status
                : '未知'}
            </dd>
          </div>

          <div>
            <dt>报告抓取状态</dt>
            <dd>
              {reportCrawlStatusLabels[report.crawl_status] ??
                report.crawl_status}
            </dd>
          </div>

          <div>
            <dt>AI 处理状态</dt>
            <dd>{reportAIStatusLabels[report.ai_status] ?? report.ai_status}</dd>
          </div>

          <div>
            <dt>PDF 链接</dt>
            <dd>
              {documentType.isPdf && report.pdf_url ? (
                <a href={report.pdf_url} target="_blank" rel="noreferrer">
                  打开 PDF
                </a>
              ) : documentType.isPdf ? (
                '暂无'
              ) : (
                '网页正文'
              )}
            </dd>
          </div>

          <div>
            <dt>页数</dt>
            <dd>
              {documentType.isPdf ? report.page_count ?? '未知' : '不适用'}
            </dd>
          </div>

          <div>
            <dt>有效文本页</dt>
            <dd>
              {documentType.isPdf
                ? report.non_empty_page_count ?? '未知'
                : '不适用'}
            </dd>
          </div>

          <div>
            <dt>PDF 大小</dt>
            <dd>
              {documentType.isPdf && report.pdf_byte_length
                ? `${Math.round(report.pdf_byte_length / 1024)} KB`
                : documentType.isPdf
                  ? '未知'
                  : '不适用'}
            </dd>
          </div>

          <div>
            <dt>成果字数</dt>
            <dd>
              原文 {countTextChars(report.content)} 字 / 翻译{' '}
              {countTextChars(report.translation)} 字 / 主要观点{' '}
              {countTextChars(report.summary)} 字 / 深层研判{' '}
              {countTextChars(report.commentary)} 字
            </dd>
          </div>
        </dl>
      </section>
    </div>
  );
}
