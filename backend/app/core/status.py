from enum import StrEnum


class ReportCrawlStatus(StrEnum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"


class CrawlRunStatus(StrEnum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"


class ReportAIStatus(StrEnum):
    pending = "pending"
    queued = "queued"
    processing = "processing"
    finalize_queued = "finalize_queued"
    finalizing = "finalizing"
    success = "success"
    failed = "failed"
    skipped = "skipped"


class ReportReviewStatus(StrEnum):
    pending_review = "pending_review"
    approved = "approved"
    needs_rerun = "needs_rerun"
    rejected = "rejected"


REPORT_REVIEW_STATUS_LABELS = {
    ReportReviewStatus.pending_review.value: "待复核",
    ReportReviewStatus.approved.value: "已通过",
    ReportReviewStatus.needs_rerun.value: "需重跑",
    ReportReviewStatus.rejected.value: "不采用",
}


def get_report_review_status_label(value: str | None) -> str:
    if not value:
        return "待复核"

    return REPORT_REVIEW_STATUS_LABELS.get(value, value)


class AIChunkType(StrEnum):
    translation = "translation"
    analysis = "analysis"


class AIChunkStatus(StrEnum):
    pending = "pending"
    queued = "queued"
    processing = "processing"
    success = "success"
    failed = "failed"


class CrawlCandidateStatus(StrEnum):
    discovered = "discovered"
    skipped = "skipped"
    saved = "saved"


class CrawlCandidateSkipReason(StrEnum):
    invalid_url = "invalid_url"
    duplicate_in_feed = "duplicate_in_feed"
    duplicate_existing = "duplicate_existing"
    document_failed = "document_failed"
    relevance_failed = "relevance_failed"
    non_china_related = "non_china_related"
    concurrent_duplicate = "concurrent_duplicate"


class NotificationEventType(StrEnum):
    report_created = "report.created"
    report_ai_completed = "report.ai_completed"
    report_ai_failed = "report.ai_failed"
    report_fetch_failed = "report.fetch_failed"
    report_review_needs_rerun = "report.review_needs_rerun"
    daily_summary = "daily_summary"
