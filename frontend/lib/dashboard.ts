import { apiRequest } from '@/lib/api';
import type { CrawlCandidateCount } from '@/lib/institution';

export type DashboardOverview = {
  think_tanks: number;
  sources: number;
  reports: number;
  pending_crawl_runs: number;
  running_crawl_runs: number;
  pending_ai_reports: number;
  running_ai_reports: number;
  failed_ai_reports: number;
  unread_notifications: number;
};

export type DashboardSourceFailure = {
  source_id: number;
  think_tank_name: string;
  url: string;
  last_error: string | null;
  last_crawled_at: string | null;
};

export type DashboardSourceHealth = {
  total_sources: number;
  active_sources: number;
  healthy_sources: number;
  warning_sources: number;
  failed_sources: number;
  never_crawled_sources: number;
  disabled_sources: number;
  recent_failures: DashboardSourceFailure[];
};

export type DashboardCrawlCandidates = {
  total: number;
  by_status: CrawlCandidateCount[];
  by_skip_reason: CrawlCandidateCount[];
};

export type DashboardData = {
  overview: DashboardOverview;
  source_health: DashboardSourceHealth;
  crawl_candidates: DashboardCrawlCandidates;
};

export async function fetchDashboard(): Promise<DashboardData> {
  return apiRequest<DashboardData>('/api/v1/dashboard');
}
