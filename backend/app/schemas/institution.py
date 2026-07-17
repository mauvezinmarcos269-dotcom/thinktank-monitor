from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator

from app.models.source import CrawlStatusEnum, SourceTypeEnum
from app.models.think_tank import OrganizationTypeEnum


class ThinkTankBase(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=255,
    )

    name_en: str | None = Field(
        default=None,
        max_length=255,
    )

    country: str = Field(
        min_length=1,
        max_length=100,
    )

    website: AnyHttpUrl | None = None

    description: str | None = Field(
        default=None,
        max_length=10000,
    )

    organization_type: OrganizationTypeEnum = OrganizationTypeEnum.think_tank

    parent_id: int | None = Field(
        default=None,
        gt=0,
    )

    is_key: bool = False
    is_active: bool = True


class ThinkTankCreate(ThinkTankBase):
    """创建智库/研究机构。"""


class ThinkTankUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    name_en: str | None = Field(
        default=None,
        max_length=255,
    )

    country: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    website: AnyHttpUrl | None = None

    description: str | None = Field(
        default=None,
        max_length=10000,
    )

    organization_type: OrganizationTypeEnum | None = None

    parent_id: int | None = Field(
        default=None,
        gt=0,
    )

    is_key: bool | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_not_empty(self) -> "ThinkTankUpdate":
        if not self.model_fields_set:
            raise ValueError("至少需要提供一个待更新字段。")
        return self


class ThinkTankRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    name_en: str | None
    country: str
    website: str | None
    description: str | None

    organization_type: OrganizationTypeEnum
    parent_id: int | None

    is_key: bool
    is_active: bool

    created_at: datetime
    updated_at: datetime


class SourceBase(BaseModel):
    source_type: SourceTypeEnum

    url: AnyHttpUrl

    crawl_frequency_minutes: int = Field(
        default=1440,
        ge=5,
        le=43200,
        description="抓取周期，单位为分钟；建议最小 5 分钟，最大 30 天。",
    )

    is_active: bool = True


class SourceCreate(SourceBase):
    """创建来源。"""


class SourceUpdate(BaseModel):
    source_type: SourceTypeEnum | None = None

    url: AnyHttpUrl | None = None

    crawl_frequency_minutes: int | None = Field(
        default=None,
        ge=5,
        le=43200,
    )

    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_not_empty(self) -> "SourceUpdate":
        if not self.model_fields_set:
            raise ValueError("至少需要提供一个待更新字段。")
        return self


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    think_tank_id: int

    source_type: SourceTypeEnum
    url: str
    crawl_frequency_minutes: int
    is_active: bool

    last_crawl_status: CrawlStatusEnum
    last_crawled_at: datetime | None
    last_error: str | None

    created_at: datetime
    updated_at: datetime


class ThinkTankDetailRead(ThinkTankRead):
    sources: list[SourceRead] = []
