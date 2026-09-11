from datetime import datetime

from pydantic import BaseModel

from app.schemas.institution import CrawlCandidateCountRead


class DashboardOverview(BaseModel):
    think_tanks: int
    sources: int
    reports: int
    pending_crawl_runs: int
    running_crawl_runs: int
    pending_ai_reports: int
    running_ai_reports: int
    failed_ai_reports: int
    unread_notifications: int


class DashboardSourceFailure(BaseModel):
    source_id: int
    think_tank_name: str
    url: str
    last_error: str | None
    last_crawled_at: datetime | None


class DashboardSourceHealth(BaseModel):
    total_sources: int
    active_sources: int
    healthy_sources: int
    warning_sources: int
    failed_sources: int
    never_crawled_sources: int
    disabled_sources: int
    recent_failures: list[DashboardSourceFailure]


class DashboardCrawlCandidates(BaseModel):
    total: int
    by_status: list[CrawlCandidateCountRead]
    by_skip_reason: list[CrawlCandidateCountRead]


class DashboardResponse(BaseModel):
    overview: DashboardOverview
    source_health: DashboardSourceHealth
    crawl_candidates: DashboardCrawlCandidates
