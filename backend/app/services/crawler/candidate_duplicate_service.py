from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.status import CrawlCandidateSkipReason, CrawlCandidateStatus
from app.models import CrawlCandidate, Report
from app.services.crawl_candidate_service import mark_candidate_skipped
from app.services.crawl_quality_service import CrawlQualityStats

CandidateDuplicateKind = Literal["report", "pending_candidate"]


@dataclass(frozen=True)
class CandidateDuplicateIndex:
    report_urls: frozenset[str] = frozenset()
    report_pdf_urls: frozenset[str] = frozenset()
    pending_urls: frozenset[str] = frozenset()
    pending_pdf_urls: frozenset[str] = frozenset()

    def classify(self, candidate: CrawlCandidate) -> CandidateDuplicateKind | None:
        if (
            candidate.normalized_url in self.report_urls
            or candidate.pdf_url in self.report_pdf_urls
        ):
            return "report"

        if (
            candidate.normalized_url in self.pending_urls
            or candidate.pdf_url in self.pending_pdf_urls
        ):
            return "pending_candidate"

        return None


def _non_empty(values: Iterable[str | None]) -> set[str]:
    return {value for value in values if value}


async def build_candidate_duplicate_index(
    db: AsyncSession,
    *,
    candidates: Iterable[CrawlCandidate],
    exclude_crawl_run_id: int,
) -> CandidateDuplicateIndex:
    candidate_list = list(candidates)
    normalized_urls = _non_empty(candidate.normalized_url for candidate in candidate_list)
    pdf_urls = _non_empty(candidate.pdf_url for candidate in candidate_list)

    if not normalized_urls and not pdf_urls:
        return CandidateDuplicateIndex()

    report_conditions = []
    pending_conditions = []

    if normalized_urls:
        report_conditions.append(Report.normalized_url.in_(normalized_urls))
        pending_conditions.append(CrawlCandidate.normalized_url.in_(normalized_urls))
    if pdf_urls:
        report_conditions.append(Report.pdf_url.in_(pdf_urls))
        pending_conditions.append(CrawlCandidate.pdf_url.in_(pdf_urls))

    report_rows = (
        await db.execute(
            select(Report.normalized_url, Report.pdf_url).where(
                or_(*report_conditions)
            )
        )
    ).all()
    pending_rows = (
        await db.execute(
            select(CrawlCandidate.normalized_url, CrawlCandidate.pdf_url).where(
                CrawlCandidate.crawl_run_id != exclude_crawl_run_id,
                CrawlCandidate.status == CrawlCandidateStatus.pending_relevance.value,
                or_(*pending_conditions),
            )
        )
    ).all()

    return CandidateDuplicateIndex(
        report_urls=frozenset(_non_empty(row.normalized_url for row in report_rows)),
        report_pdf_urls=frozenset(_non_empty(row.pdf_url for row in report_rows)),
        pending_urls=frozenset(_non_empty(row.normalized_url for row in pending_rows)),
        pending_pdf_urls=frozenset(_non_empty(row.pdf_url for row in pending_rows)),
    )


def mark_duplicate_candidate(
    candidate: CrawlCandidate,
    *,
    duplicate_kind: CandidateDuplicateKind | None,
    quality_stats: CrawlQualityStats,
    url: object,
) -> bool:
    if duplicate_kind == "report":
        mark_candidate_skipped(
            candidate,
            reason_code=CrawlCandidateSkipReason.duplicate_existing.value,
        )
        quality_stats.duplicate_existing += 1
        quality_stats.add_sample("已入库重复", url)
        return True

    if duplicate_kind == "pending_candidate":
        mark_candidate_skipped(
            candidate,
            reason_code=CrawlCandidateSkipReason.duplicate_pending.value,
        )
        quality_stats.duplicate_pending += 1
        quality_stats.add_sample("已有待授权候选", url)
        return True

    return False
