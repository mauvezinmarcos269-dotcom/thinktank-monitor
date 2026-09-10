from __future__ import annotations

import csv
from io import StringIO

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crawl_candidate import CrawlCandidate
from app.schemas.institution import (
    CrawlCandidateCountRead,
    CrawlCandidateListResponse,
    CrawlCandidateRead,
    CrawlCandidateStatisticsResponse,
)

CANDIDATE_STATUS_DISCOVERED = "discovered"
CANDIDATE_STATUS_SKIPPED = "skipped"
CANDIDATE_STATUS_SAVED = "saved"

CANDIDATE_STATUS_LABELS = {
    CANDIDATE_STATUS_DISCOVERED: "已发现",
    CANDIDATE_STATUS_SKIPPED: "已跳过",
    CANDIDATE_STATUS_SAVED: "已入库",
}

SKIP_REASON_LABELS = {
    "invalid_url": "无效 URL",
    "duplicate_in_feed": "同一来源内重复",
    "duplicate_existing": "已入库重复",
    "document_failed": "PDF 获取或页数/文本检查失败",
    "relevance_failed": "涉华判断失败",
    "non_china_related": "非涉华",
    "concurrent_duplicate": "并发重复入库",
}


def get_skip_reason_label(code: str) -> str:
    return SKIP_REASON_LABELS.get(code, code)


def get_candidate_status_label(code: str) -> str:
    return CANDIDATE_STATUS_LABELS.get(code, code)


def mark_candidate_skipped(
    candidate: CrawlCandidate,
    *,
    reason_code: str,
    error: object | None = None,
) -> None:
    candidate.status = CANDIDATE_STATUS_SKIPPED
    candidate.skip_reason_code = reason_code
    candidate.skip_reason_label = get_skip_reason_label(reason_code)

    if error is not None:
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
        base_statement = self._apply_filters(
            select(CrawlCandidate),
            crawl_run_id=crawl_run_id,
            source_id=source_id,
            status=status,
            skip_reason_code=skip_reason_code,
            skip_reason_label=skip_reason_label,
        )
        total_statement = self._apply_filters(
            select(func.count(CrawlCandidate.id)),
            crawl_run_id=crawl_run_id,
            source_id=source_id,
            status=status,
            skip_reason_code=skip_reason_code,
            skip_reason_label=skip_reason_label,
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
                    func.count(CrawlCandidate.id),
                ),
                **base_filters,
            )
            .where(CrawlCandidate.skip_reason_label.is_not(None))
            .group_by(CrawlCandidate.skip_reason_code, CrawlCandidate.skip_reason_label)
            .order_by(func.count(CrawlCandidate.id).desc())
        )

        total = await db.scalar(total_statement)
        status_rows = (await db.execute(status_statement)).all()
        reason_rows = (await db.execute(reason_statement)).all()

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
                    count=int(count),
                )
                for reason_code, reason_label, count in reason_rows
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
            skip_reason_label=skip_reason_label,
        ).order_by(
            CrawlCandidate.created_at.desc(),
            CrawlCandidate.id.desc(),
        )
        rows = (await db.execute(statement)).scalars().all()

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
            writer.writerow(
                [
                    candidate.id,
                    candidate.crawl_run_id,
                    candidate.source_id,
                    candidate.report_id or "",
                    candidate.title or "",
                    get_candidate_status_label(candidate.status),
                    candidate.skip_reason_code or "",
                    candidate.skip_reason_label or "",
                    candidate.page_count or "",
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

    def _to_read(self, candidate: CrawlCandidate) -> CrawlCandidateRead:
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
            skip_reason_label=candidate.skip_reason_label,
            error=candidate.error,
            relevance=candidate.relevance,
            relevance_reason=candidate.relevance_reason,
            is_china_related=candidate.is_china_related,
            pdf_url=candidate.pdf_url,
            page_count=candidate.page_count,
            non_empty_page_count=candidate.non_empty_page_count,
            pdf_byte_length=candidate.pdf_byte_length,
            created_at=candidate.created_at,
            updated_at=candidate.updated_at,
        )

    def _format_bool(self, value: bool | None) -> str:
        if value is None:
            return "未判断"

        return "是" if value else "否"


crawl_candidate_service = CrawlCandidateService()
