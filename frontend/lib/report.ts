import { API_BASE_URL, apiRequest } from '@/lib/api';
import { getAccessToken } from '@/lib/auth';

export type ReportCrawlStatus =
  | 'pending'
  | 'running'
  | 'success'
  | 'failed';

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
  published_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  crawl_status: ReportCrawlStatus;
  content_fetched_at: string | null;
  crawl_error: string | null;
  ai_status: string;
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
  chunk_type: string;
  chunk_index: number;
  chunk_count: number;
  status: string;
  retry_count: number;
  last_error: string | null;
  updated_at: string;
};

export type AIChunkTypeProgress = {
  chunk_type: string;
  total: number;
  pending: number;
  queued: number;
  processing: number;
  success: number;
  failed: number;
};

export type AIProgress = {
  report_id: number;
  ai_status: string;
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

export type ManualAIResponse = {
  message: string;
  report_id: number;
  ai_status: string;
  task_id: string | null;
  updated_at: string | null;
};

export type ReportListResponse = {
  items: Report[];
  total: number;
  skip: number;
  limit: number;
};

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

export async function retryReportAI(
  reportId: number
): Promise<ManualAIResponse> {
  return apiRequest<ManualAIResponse>(`/api/v1/reports/${reportId}/retry-ai`, {
    method: 'POST',
  });
}

export async function downloadReportExport(reportId: number): Promise<Blob> {
  return downloadReportFile(reportId, "export");
}

export async function downloadReportDocxExport(reportId: number): Promise<Blob> {
  return downloadReportFile(reportId, "export-docx");
}

async function downloadReportFile(
  reportId: number,
  exportPath: "export" | "export-docx"
): Promise<Blob> {
  const token = getAccessToken();

  const response = await fetch(
    `${API_BASE_URL}/api/v1/reports/${reportId}/${exportPath}`,
    {
      headers: {
        ...(token
          ? {
              Authorization: `Bearer ${token}`,
            }
          : {}),
      },
    }
  );

  if (!response.ok) {
    throw new Error(`导出失败：${response.status}`);
  }

  return response.blob();
}

export async function fetchReports(params?: {
  skip?: number;
  limit?: number;
}): Promise<ReportListResponse> {
  const query = new URLSearchParams();

  if (typeof params?.skip === 'number') {
    query.set('skip', String(params.skip));
  }

  if (typeof params?.limit === 'number') {
    query.set('limit', String(params.limit));
  }

  const queryString = query.toString();

  return apiRequest<ReportListResponse>(
    `/api/v1/reports${queryString ? `?${queryString}` : ''}`
  );
}

export async function fetchReport(reportId: number): Promise<Report> {
  return apiRequest<Report>(`/api/v1/reports/${reportId}`);
}
