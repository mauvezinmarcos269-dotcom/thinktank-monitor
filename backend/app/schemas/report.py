from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportBase(BaseModel):
    source_id: int
    title: str = Field(..., max_length=500)
    url: str

    normalized_url: str | None = None
    content_hash: str | None = Field(default=None, max_length=64)
    content: str | None = None
    published_at: datetime | None = None
    analysis_status: str = Field(
        default="pending",
        max_length=30,
    )


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
    published_at: datetime | None = None
    analysis_status: str | None = Field(
        default=None,
        max_length=30,
    )


class ReportRead(ReportBase):
    """API 返回报告时使用。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
