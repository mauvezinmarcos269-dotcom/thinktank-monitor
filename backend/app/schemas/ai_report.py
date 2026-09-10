from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AIAnalysisRead(BaseModel):
    """
    AI 分析结果读取模型。
    从 Report 实体中独立抽取，避免污染列表查询。
    """
    report_id: int

    translation: str | None = None
    summary: str | None = None
    commentary: str | None = None

    ai_status: str = Field(max_length=30)
    ai_generated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AIAnalysisUpdate(BaseModel):
    """
    如果后续你需要允许管理员手动修改 AI 生成的翻译或点评，可以使用此模型。
    """
    translation: str | None = None
    summary: str | None = None
    commentary: str | None = None
    ai_status: str | None = Field(default=None, max_length=30)


class AIChunkProgressRead(BaseModel):
    id: int
    chunk_type: str
    chunk_index: int
    chunk_count: int
    status: str
    retry_count: int
    last_error: str | None = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIChunkTypeProgressRead(BaseModel):
    chunk_type: str
    total: int
    pending: int = 0
    queued: int = 0
    processing: int = 0
    success: int = 0
    failed: int = 0


class AIProgressRead(BaseModel):
    report_id: int
    ai_status: str
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
    ai_status: str
    task_id: str | None
    updated_at: datetime | None = None
