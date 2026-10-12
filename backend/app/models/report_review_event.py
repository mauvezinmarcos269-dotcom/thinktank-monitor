from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.status import ReportReviewStatus
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.report import Report
    from app.models.user import User


class ReportReviewEvent(Base):
    """报告复核历史记录。"""

    __tablename__ = "report_review_events"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    report_id: Mapped[int] = mapped_column(
        ForeignKey(
            "reports.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    review_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=ReportReviewStatus.pending_review.value,
        server_default=ReportReviewStatus.pending_review.value,
        index=True,
    )

    review_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    reviewer_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    report: Mapped["Report"] = relationship(
        "Report",
        back_populates="review_events",
    )

    reviewer: Mapped["User | None"] = relationship(
        "User",
    )
