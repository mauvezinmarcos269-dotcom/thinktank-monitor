from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ReportCrawlStatusEnum(str, Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"


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
    published_at: datetime | None = None


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
    published_at: datetime | None = None


class ReportRead(ReportBase):
    """API 返回报告时使用。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    crawl_status: ReportCrawlStatusEnum = ReportCrawlStatusEnum.pending
    content_fetched_at: datetime | None = None
    crawl_error: str | None = None

    # AI 分析结果
    ai_status: str = "pending"
    translation: str | None = None
    summary: str | None = None
    commentary: str | None = None
    ai_generated_at: datetime | None = None


class ReportListResponse(BaseModel):
    """分页返回报告列表。"""

    items: list[ReportRead]
    total: int
    skip: int
    limit: int


class ManualCrawlResponse(BaseModel):
    """手动抓取任务提交后的响应。"""
    model_config = ConfigDict(from_attributes=True)

    message: str
    report_id: int
    crawl_status: str
    task_id: str | None = None
    updated_at: datetime | None = None
