from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from .base import Base


class CrawlRun(Base):

    __tablename__="crawl_runs"


    id=Column(
        Integer,
        primary_key=True
    )


    source_id=Column(
        Integer,
        ForeignKey(
            "sources.id"
        ),
        nullable=False
    )


    status=Column(
        String(30),
        default="pending"
    )


    found_count=Column(
        Integer,
        default=0
    )


    saved_count=Column(
        Integer,
        default=0
    )


    error=Column(
        Text
    )


    started_at=Column(
        DateTime
    )


    finished_at=Column(
        DateTime
    )


    created_at=Column(
        DateTime,
        default=datetime.utcnow
    )
