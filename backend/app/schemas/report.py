from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.status import ReportAIStatus, ReportCrawlStatus, ReportReviewStatus


class ReportBase(BaseModel):
    source_id: int
    title: str = Field(..., max_length=500)
    url: str

    normalized_url: str | None = None
    content_hash: str | None = Field(default=None, max_length=64)
    content: str | None = None
    pdf_url: str | None = None
    page_count: int | None = Field(default=None, ge=0)
    non_empty_page_count: int | None = Field(default=None, ge=0)
    pdf_byte_length: int | None = Field(default=None, ge=0)
    content_kind: str = Field(default="pdf", max_length=30)
    published_at: datetime | None = None
    review_status: ReportReviewStatus = ReportReviewStatus.pending_review
    review_note: str | None = Field(default=None, max_length=4000)


class ReportCreate(ReportBase):
    """创建报告时使用。"""
    pass


class ReportUpdate(BaseModel):
    """更新报告时使用，所有字段均为可选。"""

    source_id: int | None = None
    title: str | None = Field(default=None, max_length=500)
    url: str | None = None

    normalized_url: str | None = None
    content_hash: str | None = Field(default=None, max_length=64)
    content: str | None = None
    pdf_url: str | None = None
    page_count: int | None = Field(default=None, ge=0)
    non_empty_page_count: int | None = Field(default=None, ge=0)
    pdf_byte_length: int | None = Field(default=None, ge=0)
    content_kind: str | None = Field(default=None, max_length=30)
    published_at: datetime | None = None
    review_status: ReportReviewStatus | None = None
    review_note: str | None = Field(default=None, max_length=4000)


class ReportBatchReviewUpdate(BaseModel):
    """批量更新报告复核状态。"""

    report_ids: list[int] = Field(..., min_length=1, max_length=100)
    review_status: ReportReviewStatus


class ReportBatchExportRequest(BaseModel):
    """批量导出报告成果。"""

    report_ids: list[int] = Field(..., min_length=1, max_length=100)
    export_format: Literal["markdown", "docx"] = "docx"


class ReportRead(ReportBase):
    """API 返回报告时使用。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    reviewed_at: datetime | None = None

    crawl_status: ReportCrawlStatus = ReportCrawlStatus.pending
    content_fetched_at: datetime | None = None
    crawl_error: str | None = None

    # AI 生成结果：
    # summary 字段因历史兼容保留原名，业务含义为“主要观点”。
    ai_status: ReportAIStatus = ReportAIStatus.pending
    translation: str | None = None
    summary: str | None = Field(
        default=None,
        description="分析评论稿第一部分：主要观点。",
    )
    commentary: str | None = Field(
        default=None,
        description="分析评论稿第二部分：深层研判。",
    )
    ai_generated_at: datetime | None = None


class ReportListResponse(BaseModel):
    """分页返回报告列表。"""

    items: list[ReportRead]
    total: int
    skip: int
    limit: int


class ReportBatchReviewResponse(BaseModel):
    """批量复核状态更新结果。"""

    items: list[ReportRead]
    updated_count: int
    not_found_ids: list[int]


class ReportReviewEventRead(BaseModel):
    """报告复核历史记录。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    report_id: int
    review_status: ReportReviewStatus
    review_note: str | None = None
    reviewer_id: int | None = None
    reviewer_email: str | None = None
    created_at: datetime


class ManualCrawlResponse(BaseModel):
    """手动抓取任务提交后的响应。"""
    model_config = ConfigDict(from_attributes=True)

    message: str
    report_id: int
    crawl_status: ReportCrawlStatus
    task_id: str | None = None
    updated_at: datetime | None = None
