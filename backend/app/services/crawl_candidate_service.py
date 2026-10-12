from __future__ import annotations

import csv
import re
from collections import Counter
from io import StringIO

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.content_kind import ReportContentKind, get_content_kind_label
from app.core.llm_authorization import document_hash
from app.core.status import CrawlCandidateSkipReason, CrawlCandidateStatus
from app.models.crawl_candidate import CrawlCandidate
from app.schemas.institution import (
    CrawlCandidateCountRead,
    CrawlCandidateListResponse,
    CrawlCandidateRead,
    CrawlCandidateStatisticsResponse,
)
from app.services.candidate_skip_reason import get_skip_reason_label
from app.services.crawler.report_document_service import (
    ReportDocumentResult,
    ReportDocumentValidationError,
)

CANDIDATE_STATUS_DISCOVERED = CrawlCandidateStatus.discovered.value
CANDIDATE_STATUS_PENDING_RELEVANCE = CrawlCandidateStatus.pending_relevance.value
CANDIDATE_STATUS_SKIPPED = CrawlCandidateStatus.skipped.value
CANDIDATE_STATUS_SAVED = CrawlCandidateStatus.saved.value

CANDIDATE_STATUS_LABELS = {
    CANDIDATE_STATUS_DISCOVERED: "已发现",
    CANDIDATE_STATUS_PENDING_RELEVANCE: "待授权",
    CANDIDATE_STATUS_SKIPPED: "已跳过",
    CANDIDATE_STATUS_SAVED: "已入库",
}


def get_candidate_status_label(code: str) -> str:
    return CANDIDATE_STATUS_LABELS.get(code, code)


def set_candidate_document_metadata(
    candidate: CrawlCandidate,
    document: ReportDocumentResult,
) -> None:
    candidate.document_hash = document_hash(candidate.title or "", document.text)
    candidate.content_length = len(document.text)
    candidate.pdf_url = document.pdf_url
    candidate.page_count = document.page_count
    candidate.non_empty_page_count = document.non_empty_page_count
    candidate.pdf_byte_length = document.pdf_byte_length
    candidate.content_kind = document.content_kind


def _document_display_metadata(
    *,
    page_count: int | None,
    content_kind: str | None,
    skip_reason_code: str | None,
    error: str | None,
) -> tuple[int | None, str | None]:
    # 旧候选只保存了页数错误文字；仅用明确的检查结果补齐缺失展示字段。
    if skip_reason_code == CrawlCandidateSkipReason.document_failed.value and error:
        match = re.fullmatch(
            r"(?:ValueError:\s*)?报告页数不足[：:]\s*(\d+)\s*页[，,]\s*"
            r"要求至少\s*(\d+)\s*页[。.]?",
            error.strip(),
        )

        if match and 0 < int(match[1]) < int(match[2]):
            if page_count is None:
                page_count = int(match[1])
            if content_kind is None:
                content_kind = ReportContentKind.pdf.value

    return page_count, content_kind


def mark_candidate_skipped(
    candidate: CrawlCandidate,
    *,
    reason_code: str,
    error: object | None = None,
) -> None:
    candidate.status = CANDIDATE_STATUS_SKIPPED
    candidate.skip_reason_code = reason_code
    candidate.skip_reason_label = get_skip_reason_label(reason_code, error=error)

    if error is not None:
        candidate.error = str(error)[:5000]

    if (
        reason_code == CrawlCandidateSkipReason.document_failed.value
        and isinstance(error, ReportDocumentValidationError)
    ):
        set_candidate_document_metadata(candidate, error.document)


def mark_candidate_pending_relevance(
    candidate: CrawlCandidate,
    *,
    error: object,
) -> None:
    candidate.status = CANDIDATE_STATUS_PENDING_RELEVANCE
    candidate.skip_reason_code = None
    candidate.skip_reason_label = None
    candidate.relevance = None
    candidate.relevance_reason = None
    candidate.is_china_related = None
    candidate.error = str(error)[:5000]


def mark_candidate_saved(candidate: CrawlCandidate, *, report_id: int) -> None:
    candidate.status = CANDIDATE_STATUS_SAVED
    candidate.report_id = report_id
    candidate.skip_reason_code = None
    candidate.skip_reason_label = None
    candidate.error = None


class CrawlCandidateService:
    async def get_recent_candidates(
        self,
        db: AsyncSession,
        *,
        crawl_run_id: int | None = None,
        source_id: int | None = None,
        status: str | None = None,
        skip_reason_code: str | None = None,
        skip_reason_label: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> CrawlCandidateListResponse:
        if skip_reason_label:
            statement = self._apply_filters(
                select(CrawlCandidate),
                crawl_run_id=crawl_run_id,
                source_id=source_id,
                status=status,
                skip_reason_code=skip_reason_code,
                skip_reason_label=None,
            ).order_by(
                CrawlCandidate.created_at.desc(),
                CrawlCandidate.id.desc(),
            )
            matched_rows = [
                candidate
                for candidate in (await db.execute(statement)).scalars().all()
                if self._skip_reason_label(candidate) == skip_reason_label
            ]
            total = len(matched_rows)
            rows = matched_rows[skip : skip + limit]
        else:
            base_statement = self._apply_filters(
                select(CrawlCandidate),
                crawl_run_id=crawl_run_id,
                source_id=source_id,
                status=status,
                skip_reason_code=skip_reason_code,
                skip_reason_label=None,
            )
            total_statement = self._apply_filters(
                select(func.count(CrawlCandidate.id)),
                crawl_run_id=crawl_run_id,
                source_id=source_id,
                status=status,
                skip_reason_code=skip_reason_code,
                skip_reason_label=None,
            )

            statement = base_statement.order_by(
                CrawlCandidate.created_at.desc(),
                CrawlCandidate.id.desc(),
            ).offset(skip).limit(limit)

            total = await db.scalar(total_statement)
            rows = (await db.execute(statement)).scalars().all()

        return CrawlCandidateListResponse(
            items=[self._to_read(candidate) for candidate in rows],
            total=int(total or 0),
            skip=skip,
            limit=limit,
        )

    async def get_statistics(
        self,
        db: AsyncSession,
        *,
        crawl_run_id: int | None = None,
        source_id: int | None = None,
    ) -> CrawlCandidateStatisticsResponse:
        base_filters = {
            "crawl_run_id": crawl_run_id,
            "source_id": source_id,
            "status": None,
            "skip_reason_code": None,
            "skip_reason_label": None,
        }
        total_statement = self._apply_filters(
            select(func.count(CrawlCandidate.id)),
            **base_filters,
        )
        status_statement = (
            self._apply_filters(
                select(CrawlCandidate.status, func.count(CrawlCandidate.id)),
                **base_filters,
            )
            .group_by(CrawlCandidate.status)
            .order_by(CrawlCandidate.status.asc())
        )
        reason_statement = (
            self._apply_filters(
                select(
                    CrawlCandidate.skip_reason_code,
                    CrawlCandidate.skip_reason_label,
                    CrawlCandidate.error,
                    CrawlCandidate.page_count,
                    CrawlCandidate.content_kind,
                ),
                **base_filters,
            )
            .where(CrawlCandidate.skip_reason_code.is_not(None))
        )
        content_kind_statement = (
            self._apply_filters(
                select(
                    CrawlCandidate.content_kind,
                    func.count(CrawlCandidate.id),
                ),
                **base_filters,
            )
            .group_by(CrawlCandidate.content_kind)
            .order_by(func.count(CrawlCandidate.id).desc())
        )

        total = await db.scalar(total_statement)
        status_rows = (await db.execute(status_statement)).all()
        reason_rows = (await db.execute(reason_statement)).all()
        content_kind_rows = (await db.execute(content_kind_statement)).all()
        reason_counts: Counter[tuple[str | None, str]] = Counter()
        content_kind_counts: Counter[str | None] = Counter(dict(content_kind_rows))

        for reason_code, reason_label, error, page_count, content_kind in reason_rows:
            display_label = get_skip_reason_label(
                reason_code,
                error=error,
                stored_label=reason_label,
            )
            reason_counts[(reason_code, display_label)] += 1

            _, display_kind = _document_display_metadata(
                page_count=page_count,
                content_kind=content_kind,
                skip_reason_code=reason_code,
                error=error,
            )
            if display_kind != content_kind:
                content_kind_counts[content_kind] -= 1
                content_kind_counts[display_kind] += 1

        return CrawlCandidateStatisticsResponse(
            total=int(total or 0),
            by_status=[
                CrawlCandidateCountRead(
                    code=status,
                    label=get_candidate_status_label(status),
                    count=int(count),
                )
                for status, count in status_rows
            ],
            by_skip_reason=[
                CrawlCandidateCountRead(
                    code=reason_code,
                    label=reason_label,
                    count=count,
                )
                for (reason_code, reason_label), count in sorted(
                    reason_counts.items(),
                    key=lambda item: (-item[1], item[0][1]),
                )
            ],
            by_content_kind=[
                CrawlCandidateCountRead(
                    code=content_kind,
                    label=get_content_kind_label(content_kind),
                    count=int(count),
                )
                for content_kind, count in sorted(
                    content_kind_counts.items(),
                    key=lambda item: (-item[1], item[0] or ""),
                )
                if count > 0
            ],
        )

    async def build_csv(
        self,
        db: AsyncSession,
        *,
        crawl_run_id: int | None = None,
        source_id: int | None = None,
        status: str | None = None,
        skip_reason_code: str | None = None,
        skip_reason_label: str | None = None,
    ) -> str:
        statement = self._apply_filters(
            select(CrawlCandidate),
            crawl_run_id=crawl_run_id,
            source_id=source_id,
            status=status,
            skip_reason_code=skip_reason_code,
            skip_reason_label=None,
        ).order_by(
            CrawlCandidate.created_at.desc(),
            CrawlCandidate.id.desc(),
        )
        rows = (await db.execute(statement)).scalars().all()

        if skip_reason_label:
            rows = [
                candidate
                for candidate in rows
                if self._skip_reason_label(candidate) == skip_reason_label
            ]

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "候选ID",
                "抓取运行ID",
                "来源ID",
                "报告ID",
                "标题",
                "状态",
                "跳过原因代码",
                "跳过原因",
                "内容类型",
                "页数",
                "非空页数",
                "是否涉华",
                "涉华等级",
                "涉华判断说明",
                "URL",
                "PDF URL",
                "错误摘要",
                "发现时间",
            ]
        )

        for candidate in rows:
            page_count, content_kind = _document_display_metadata(
                page_count=candidate.page_count,
                content_kind=candidate.content_kind,
                skip_reason_code=candidate.skip_reason_code,
                error=candidate.error,
            )
            writer.writerow(
                [
                    candidate.id,
                    candidate.crawl_run_id,
                    candidate.source_id,
                    candidate.report_id or "",
                    candidate.title or "",
                    get_candidate_status_label(candidate.status),
                    candidate.skip_reason_code or "",
                    self._skip_reason_label(candidate) or "",
                    content_kind or "",
                    page_count or "",
                    candidate.non_empty_page_count or "",
                    self._format_bool(candidate.is_china_related),
                    candidate.relevance or "",
                    candidate.relevance_reason or "",
                    candidate.url,
                    candidate.pdf_url or "",
                    candidate.error or "",
                    candidate.created_at.isoformat() if candidate.created_at else "",
                ]
            )

        return "\ufeff" + output.getvalue()

    def _apply_filters(
        self,
        statement: Select,
        *,
        crawl_run_id: int | None,
        source_id: int | None,
        status: str | None,
        skip_reason_code: str | None,
        skip_reason_label: str | None,
    ) -> Select:
        if crawl_run_id is not None:
            statement = statement.where(CrawlCandidate.crawl_run_id == crawl_run_id)

        if source_id is not None:
            statement = statement.where(CrawlCandidate.source_id == source_id)

        if status:
            statement = statement.where(CrawlCandidate.status == status)

        if skip_reason_code:
            statement = statement.where(
                CrawlCandidate.skip_reason_code == skip_reason_code
            )

        if skip_reason_label:
            statement = statement.where(
                CrawlCandidate.skip_reason_label == skip_reason_label
            )

        return statement

    def _skip_reason_label(self, candidate: CrawlCandidate) -> str:
        return get_skip_reason_label(
            candidate.skip_reason_code,
            error=candidate.error,
            stored_label=candidate.skip_reason_label,
        )

    def _to_read(self, candidate: CrawlCandidate) -> CrawlCandidateRead:
        page_count, content_kind = _document_display_metadata(
            page_count=candidate.page_count,
            content_kind=candidate.content_kind,
            skip_reason_code=candidate.skip_reason_code,
            error=candidate.error,
        )
        return CrawlCandidateRead(
            id=candidate.id,
            crawl_run_id=candidate.crawl_run_id,
            source_id=candidate.source_id,
            report_id=candidate.report_id,
            title=candidate.title,
            url=candidate.url,
            normalized_url=candidate.normalized_url,
            status=candidate.status,
            skip_reason_code=candidate.skip_reason_code,
            skip_reason_label=self._skip_reason_label(candidate) or None,
            error=candidate.error,
            relevance=candidate.relevance,
            relevance_reason=candidate.relevance_reason,
            is_china_related=candidate.is_china_related,
            pdf_url=candidate.pdf_url,
            page_count=page_count,
            non_empty_page_count=candidate.non_empty_page_count,
            pdf_byte_length=candidate.pdf_byte_length,
            content_kind=content_kind,
            created_at=candidate.created_at,
            updated_at=candidate.updated_at,
        )

    def _format_bool(self, value: bool | None) -> str:
        if value is None:
            return "未判断"

        return "是" if value else "否"


crawl_candidate_service = CrawlCandidateService()
