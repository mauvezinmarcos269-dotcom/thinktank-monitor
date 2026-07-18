from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.source import (
    CrawlStatusEnum,
    SourceTypeEnum,
)


class SourceBase(BaseModel):

    think_tank_id: int

    source_type: SourceTypeEnum

    url: str

    crawl_frequency_minutes: int = 1440



class SourceCreate(SourceBase):
    pass



class SourceResponse(SourceBase):

    id: int

    is_active: bool

    last_crawl_status: CrawlStatusEnum

    last_crawled_at: datetime | None

    last_error: str | None


    model_config = ConfigDict(
        from_attributes=True
    )
