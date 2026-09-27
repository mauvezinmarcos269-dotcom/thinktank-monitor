'use client';

import { type ReportReviewEvent } from '@/lib/report';
import { reportReviewStatusLabels } from '@/lib/status';

import { formatDateTime } from './report-page-utils';

type ReviewHistoryPanelProps = {
  loading: boolean;
  errorMessage: string | null;
  events: ReportReviewEvent[];
};

export function ReviewHistoryPanel({
  loading,
  errorMessage,
  events,
}: ReviewHistoryPanelProps) {
  return (
    <section className="section-block">
      <h3>复核历史</h3>
      {loading && <p>正在加载复核历史……</p>}
      {errorMessage && <p className="message-error">{errorMessage}</p>}
      {events.length > 0 ? (
        <ol className="review-history">
          {events.map((event) => (
            <li key={event.id}>
              <strong>
                {reportReviewStatusLabels[event.review_status] ??
                  event.review_status}
              </strong>
              <span>
                {formatDateTime(event.created_at)} /{' '}
                {event.reviewer_email ?? '未知操作人'}
              </span>
              <p>{event.review_note || '无意见'}</p>
            </li>
          ))}
        </ol>
      ) : (
        <p>暂无复核历史。</p>
      )}
    </section>
  );
}
