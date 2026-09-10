import { apiDownload, apiRequest } from '@/lib/api';

export type ThinkTank = {
  id: number;
  key: string;
  name: string;
  name_en: string | null;
  country: string;
  website: string | null;
  description: string | null;
  organization_type: string;
  parent_id: number | null;
  is_key: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type Source = {
  id: number;
  think_tank_id: number;
  source_type: string;
  url: string;
  crawl_frequency_minutes: number;
  is_active: boolean;
  last_crawl_status: string;
  last_crawled_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
};

export type CrawlRun = {
  id: number;
  source_id: number;
  status: string;
  found_count: number;
  saved_count: number;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  duration_seconds: number | null;
};

export type CrawlCandidate = {
  id: number;
  crawl_run_id: number;
  source_id: number;
  report_id: number | null;
  title: string | null;
  url: string;
  normalized_url: string | null;
  status: string;
  skip_reason_code: string | null;
  skip_reason_label: string | null;
  error: string | null;
  relevance: string | null;
  relevance_reason: string | null;
  is_china_related: boolean | null;
  pdf_url: string | null;
  page_count: number | null;
  non_empty_page_count: number | null;
  pdf_byte_length: number | null;
  created_at: string;
  updated_at: string;
};

export type SourceHealth = Source & {
  think_tank_name: string;
  think_tank_country: string;
  latest_report_created_at: string | null;
  report_count: number;
  health_status: 'healthy' | 'warning' | 'failed' | 'never' | 'disabled';
  health_reason: string;
  diagnosis_code: string;
  diagnosis_label: string;
  diagnosis_advice: string;
  recent_crawl_runs: CrawlRun[];
};

export type SourceHealthSummary = {
  total_sources: number;
  active_sources: number;
  healthy_sources: number;
  warning_sources: number;
  failed_sources: number;
  never_crawled_sources: number;
  disabled_sources: number;
};

export type SourceHealthResponse = {
  summary: SourceHealthSummary;
  items: SourceHealth[];
};

export type CrawlCandidateResponse = {
  items: CrawlCandidate[];
  total: number;
  skip: number;
  limit: number;
};

export type CrawlCandidateCount = {
  code: string | null;
  label: string;
  count: number;
};

export type CrawlCandidateStatistics = {
  total: number;
  by_status: CrawlCandidateCount[];
  by_skip_reason: CrawlCandidateCount[];
};

export type CrawlCandidateQuery = {
  crawlRunId: number;
  skip?: number;
  limit?: number;
  status?: string;
  skipReasonLabel?: string;
};

export type InstitutionStats = {
  think_tanks: number;
  sources: number;
  total_think_tanks: number;
  active_think_tanks: number;
  key_think_tanks: number;
  total_sources: number;
  active_sources: number;
  missing_active_sources: number;
};

export type SourceCreateInput = {
  source_type: 'website' | 'rss' | 'report_library' | 'topic_page';
  url: string;
  crawl_frequency_minutes: number;
  is_active: boolean;
};

export type SourceCrawlResponse = {
  message: string;
  source_id: number;
  task_id: string;
};

export async function fetchInstitutionStats(): Promise<InstitutionStats> {
  return apiRequest<InstitutionStats>('/api/v1/think-tanks/statistics');
}

export async function fetchThinkTanks(): Promise<ThinkTank[]> {
  return apiRequest<ThinkTank[]>('/api/v1/think-tanks?is_active=true&limit=200');
}

export async function fetchMissingSourceThinkTanks(): Promise<ThinkTank[]> {
  return apiRequest<ThinkTank[]>('/api/v1/think-tanks/missing-sources?limit=500');
}

export async function fetchSources(): Promise<Source[]> {
  return apiRequest<Source[]>('/api/v1/sources?limit=500');
}

export async function fetchSourceHealth(): Promise<SourceHealthResponse> {
  return apiRequest<SourceHealthResponse>('/api/v1/sources/health?limit=500');
}

export async function fetchSourceCrawlRuns(
  sourceId?: number
): Promise<{ items: CrawlRun[] }> {
  const query = sourceId ? `?source_id=${sourceId}&limit=50` : '?limit=50';
  return apiRequest<{ items: CrawlRun[] }>(`/api/v1/sources/crawl-runs${query}`);
}

export async function fetchCrawlCandidates({
  crawlRunId,
  skip = 0,
  limit = 50,
  status,
  skipReasonLabel,
}: CrawlCandidateQuery): Promise<CrawlCandidateResponse> {
  const params = new URLSearchParams({
    crawl_run_id: String(crawlRunId),
    skip: String(skip),
    limit: String(limit),
  });

  if (status) {
    params.set('candidate_status', status);
  }

  if (skipReasonLabel) {
    params.set('skip_reason_label', skipReasonLabel);
  }

  return apiRequest<CrawlCandidateResponse>(
    `/api/v1/sources/crawl-candidates?${params.toString()}`
  );
}

export async function fetchCrawlCandidateStatistics(
  crawlRunId: number
): Promise<CrawlCandidateStatistics> {
  return apiRequest<CrawlCandidateStatistics>(
    `/api/v1/sources/crawl-candidates/statistics?crawl_run_id=${crawlRunId}`
  );
}

export async function downloadCrawlCandidatesCsv({
  crawlRunId,
  status,
  skipReasonLabel,
}: CrawlCandidateQuery): Promise<Blob> {
  const params = new URLSearchParams({
    crawl_run_id: String(crawlRunId),
  });

  if (status) {
    params.set('candidate_status', status);
  }

  if (skipReasonLabel) {
    params.set('skip_reason_label', skipReasonLabel);
  }

  return apiDownload(`/api/v1/sources/crawl-candidates/export?${params.toString()}`);
}

export async function createThinkTankSource(
  thinkTankId: number,
  input: SourceCreateInput
): Promise<Source> {
  return apiRequest<Source>(`/api/v1/think-tanks/${thinkTankId}/sources`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function triggerSourceCrawl(
  sourceId: number
): Promise<SourceCrawlResponse> {
  return apiRequest<SourceCrawlResponse>(`/api/v1/sources/${sourceId}/crawl`, {
    method: 'POST',
  });
}
