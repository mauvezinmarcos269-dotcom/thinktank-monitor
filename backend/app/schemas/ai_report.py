from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.status import (
    AIChunkStatus,
    AIChunkType,
    ReportAIStatus,
    ReportReviewStatus,
)


class AIAnalysisRead(BaseModel):
    """
    AI 分析结果读取模型。
    从 Report 实体中独立抽取，避免污染列表查询。
    """
    report_id: int

    translation: str | None = None
    summary: str | None = Field(
        default=None,
        description="分析评论稿第一部分：主要观点。",
    )
    commentary: str | None = Field(
        default=None,
        description="分析评论稿第二部分：深层研判。",
    )

    ai_status: ReportAIStatus = Field(max_length=30)
    ai_generated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AIAnalysisUpdate(BaseModel):
    """
    如果后续你需要允许管理员手动修改 AI 生成的翻译或点评，可以使用此模型。
    """
    translation: str | None = None
    summary: str | None = Field(
        default=None,
        description="分析评论稿第一部分：主要观点。",
    )
    commentary: str | None = Field(
        default=None,
        description="分析评论稿第二部分：深层研判。",
    )
    ai_status: ReportAIStatus | None = Field(default=None, max_length=30)


class AIChunkProgressRead(BaseModel):
    id: int
    chunk_type: AIChunkType
    chunk_index: int
    chunk_count: int
    status: AIChunkStatus
    retry_count: int
    last_error: str | None = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIChunkTypeProgressRead(BaseModel):
    chunk_type: AIChunkType
    total: int
    pending: int = 0
    queued: int = 0
    processing: int = 0
    success: int = 0
    failed: int = 0


class AIProgressRead(BaseModel):
    report_id: int
    ai_status: ReportAIStatus
    ai_retry_count: int
    ai_generated_at: datetime | None = None
    total_chunks: int
    completed_chunks: int
    failed_chunks: int
    running_chunks: int
    latest_error: str | None = None
    by_type: list[AIChunkTypeProgressRead]
    chunks: list[AIChunkProgressRead]


class ManualAIResponse(BaseModel):
    message: str
    report_id: int
    ai_status: ReportAIStatus
    review_status: ReportReviewStatus | None = None
    task_id: str | None
    updated_at: datetime | None = None
