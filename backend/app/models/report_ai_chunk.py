from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.status import AIChunkStatus
from app.models.base import Base


class ReportAIChunk(Base):
    """
    报告 AI 分块处理记录。

    translation:
        保存全文翻译分块结果。

    analysis:
        保存用于最终摘要和评论的分块分析笔记。
    """

    __tablename__ = "report_ai_chunks"

    __table_args__ = (
        UniqueConstraint(
            "report_id",
            "chunk_type",
            "chunk_index",
            name="uq_report_ai_chunk",
        ),
        Index(
            "ix_report_ai_chunks_report_status",
            "report_id",
            "status",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    report_id: Mapped[int] = mapped_column(
        ForeignKey(
            "reports.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    # translation / analysis
    chunk_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    # 从 1 开始，例如 1/8、2/8……
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    chunk_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # 对应 Report.content 中的字符区间：
    # content[source_start:source_end]
    source_start: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    source_end: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # 创建分块时对应的完整 Report.content_hash。
    # 如果正文发生变化，旧分块不得继续复用。
    report_content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    # translation 类型：存中文翻译
    # analysis 类型：存该块分析笔记
    output_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # pending / processing / success / failed
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=AIChunkStatus.pending.value,
        server_default=AIChunkStatus.pending.value,
        index=True,
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
