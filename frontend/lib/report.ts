import { apiDownload, apiRequest } from '@/lib/api';
import {
  type AIChunkStatus,
  type AIChunkType,
  type ReportAIStatus,
  type ReportContentKind,
  type ReportCrawlStatus,
  type ReportDeliverableStatus,
  type ReportReviewStatus,
} from '@/lib/status';

export type Report = {
  id: number;
  source_id: number;
  title: string;
  url: string;
  normalized_url: string | null;
  content_hash: string | null;
  content: string | null;
  pdf_url: string | null;
  page_count: number | null;
  non_empty_page_count: number | null;
  pdf_byte_length: number | null;
  content_kind: ReportContentKind | string;
  review_status: ReportReviewStatus;
  review_note: string | null;
  reviewed_at: string | null;
  published_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  crawl_status: ReportCrawlStatus;
  content_fetched_at: string | null;
  crawl_error: string | null;
  ai_status: ReportAIStatus;
  summary: string | null;
  translation: string | null;
  commentary: string | null;
  ai_generated_at: string | null;
};

export type ManualCrawlResponse = {
  message: string;
  report_id: number;
  crawl_status: ReportCrawlStatus;
  task_id: string | null;
  updated_at: string | null;
};

export type AIChunkProgress = {
  id: number;
  chunk_type: AIChunkType;
  chunk_index: number;
  chunk_count: number;
  status: AIChunkStatus;
  retry_count: number;
  last_error: string | null;
  updated_at: string;
};

export type AIChunkTypeProgress = {
  chunk_type: AIChunkType;
  total: number;
  pending: number;
  queued: number;
  processing: number;
  success: number;
  failed: number;
};

export type AIProgress = {
  report_id: number;
  ai_status: ReportAIStatus;
  ai_retry_count: number;
  ai_generated_at: string | null;
  total_chunks: number;
  completed_chunks: number;
  failed_chunks: number;
  running_chunks: number;
  latest_error: string | null;
  by_type: AIChunkTypeProgress[];
  chunks: AIChunkProgress[];
};

export type ReportReviewEvent = {
  id: number;
  report_id: number;
  review_status: ReportReviewStatus;
  review_note: string | null;
  reviewer_id: number | null;
  reviewer_email: string | null;
  created_at: string;
};

export type ManualAIResponse = {
  message: string;
  report_id: number;
  ai_status: ReportAIStatus;
  review_status: ReportReviewStatus | null;
  task_id: string | null;
  updated_at: string | null;
};

export type ReportListResponse = {
  items: Report[];
  total: number;
  skip: number;
  limit: number;
};

export type ReportBatchReviewResponse = {
  items: Report[];
  updated_count: number;
  not_found_ids: number[];
};

export type ReportBatchExportFormat = 'markdown' | 'docx';

export type ReportUpdateInput = {
  review_status?: ReportReviewStatus;
  review_note?: string | null;
};

export async function updateReport(
  reportId: number,
  input: ReportUpdateInput
): Promise<Report> {
  return apiRequest<Report>(`/api/v1/reports/${reportId}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  });
}

export async function batchUpdateReportReviewStatus(
  reportIds: number[],
  reviewStatus: ReportReviewStatus
): Promise<ReportBatchReviewResponse> {
  return apiRequest<ReportBatchReviewResponse>('/api/v1/reports/batch-review', {
    method: 'PATCH',
    body: JSON.stringify({
      report_ids: reportIds,
      review_status: reviewStatus,
    }),
  });
}

export async function triggerFetchContent(
  reportId: number
): Promise<ManualCrawlResponse> {
  return apiRequest<ManualCrawlResponse>(
    `/api/v1/reports/${reportId}/fetch-content`,
    {
      method: 'POST',
    }
  );
}

export async function fetchAIProgress(reportId: number): Promise<AIProgress> {
  return apiRequest<AIProgress>(`/api/v1/reports/${reportId}/ai-progress`);
}

export async function fetchReportReviewEvents(
  reportId: number
): Promise<ReportReviewEvent[]> {
  return apiRequest<ReportReviewEvent[]>(
    `/api/v1/reports/${reportId}/review-events`
  );
}

export async function retryReportAI(
  reportId: number
): Promise<ManualAIResponse> {
  return apiRequest<ManualAIResponse>(`/api/v1/reports/${reportId}/retry-ai`, {
    method: 'POST',
  });
}

export async function downloadReportExport(reportId: number): Promise<Blob> {
  return apiDownload(`/api/v1/reports/${reportId}/export`);
}

export async function downloadReportDocxExport(reportId: number): Promise<Blob> {
  return apiDownload(`/api/v1/reports/${reportId}/export-docx`);
}

export async function downloadBatchReportExport(
  reportIds: number[],
  exportFormat: ReportBatchExportFormat
): Promise<Blob> {
  return apiDownload('/api/v1/reports/batch-export', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      report_ids: reportIds,
      export_format: exportFormat,
    }),
  });
}

export async function fetchReports(params?: {
  skip?: number;
  limit?: number;
  reviewStatus?: ReportReviewStatus | '';
  aiStatus?: ReportAIStatus | '';
  contentKind?: ReportContentKind | '';
  deliverableStatus?: ReportDeliverableStatus | '';
  keyword?: string;
  thinkTankId?: number | '';
  sourceId?: number | '';
}): Promise<ReportListResponse> {
  const query = new URLSearchParams();

  if (typeof params?.skip === 'number') {
    query.set('skip', String(params.skip));
  }

  if (typeof params?.limit === 'number') {
    query.set('limit', String(params.limit));
  }

  if (params?.reviewStatus) {
    query.set('review_status', params.reviewStatus);
  }

  if (params?.aiStatus) {
    query.set('ai_status', params.aiStatus);
  }

  if (params?.contentKind) {
    query.set('content_kind', params.contentKind);
  }

  if (params?.deliverableStatus) {
    query.set('deliverable_status', params.deliverableStatus);
  }

  if (params?.thinkTankId) {
    query.set('think_tank_id', String(params.thinkTankId));
  }

  if (params?.sourceId) {
    query.set('source_id', String(params.sourceId));
  }

  const keyword = params?.keyword?.trim();
  if (keyword) {
    query.set('keyword', keyword);
  }

  const queryString = query.toString();

  return apiRequest<ReportListResponse>(
    `/api/v1/reports${queryString ? `?${queryString}` : ''}`
  );
}

export async function fetchReport(reportId: number): Promise<Report> {
  return apiRequest<Report>(`/api/v1/reports/${reportId}`);
}
