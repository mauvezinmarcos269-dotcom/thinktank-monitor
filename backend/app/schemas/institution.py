from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator

from app.core.status import CrawlCandidateStatus, CrawlRunStatus
from app.models.source import CrawlStatusEnum, SourceTypeEnum
from app.models.think_tank import OrganizationTypeEnum, PriorityTierEnum, RegionFocusEnum


class ThinkTankBase(BaseModel):
    key: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9_]+$",
        description="机构稳定标识，仅允许小写字母、数字和下划线。",
    )

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
    priority_tier: PriorityTierEnum = PriorityTierEnum.p4
    region_focus: RegionFocusEnum = RegionFocusEnum.candidate

    parent_id: int | None = Field(
        default=None,
        gt=0,
    )

    is_key: bool = False
    is_verified: bool = False
    is_active: bool = True


class ThinkTankCreate(ThinkTankBase):
    """创建智库/研究机构。"""


class ThinkTankUpdate(BaseModel):
    key: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9_]+$",
    )

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
    priority_tier: PriorityTierEnum | None = None
    region_focus: RegionFocusEnum | None = None

    parent_id: int | None = Field(
        default=None,
        gt=0,
    )

    is_key: bool | None = None
    is_verified: bool | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_not_empty(self) -> "ThinkTankUpdate":
        if not self.model_fields_set:
            raise ValueError("至少需要提供一个待更新字段。")
        return self


class ThinkTankRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    name: str
    name_en: str | None
    country: str
    website: str | None
    description: str | None

    organization_type: OrganizationTypeEnum
    priority_tier: PriorityTierEnum
    region_focus: RegionFocusEnum
    parent_id: int | None

    is_key: bool
    is_verified: bool
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


class CrawlRunRead(BaseModel):
    id: int
    source_id: int
    status: CrawlRunStatus
    found_count: int
    saved_count: int
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    duration_seconds: int | None


class CrawlCandidateRead(BaseModel):
    id: int
    crawl_run_id: int
    source_id: int
    report_id: int | None
    title: str | None
    url: str
    normalized_url: str | None
    status: CrawlCandidateStatus
    skip_reason_code: str | None
    skip_reason_label: str | None
    error: str | None
    relevance: str | None
    relevance_reason: str | None
    is_china_related: bool | None
    pdf_url: str | None
    page_count: int | None
    non_empty_page_count: int | None
    pdf_byte_length: int | None
    content_kind: str | None
    created_at: datetime
    updated_at: datetime


class SourceHealthRead(SourceRead):
    think_tank_name: str
    think_tank_key: str
    think_tank_country: str
    think_tank_priority_tier: PriorityTierEnum
    think_tank_region_focus: RegionFocusEnum
    think_tank_is_verified: bool
    latest_report_created_at: datetime | None
    report_count: int
    health_status: str
    health_reason: str
    diagnosis_code: str
    diagnosis_label: str
    diagnosis_advice: str
    rollout_stage: str
    document_policy: str
    can_run_pilot_crawl: bool
    rollout_advice: str
    recent_crawl_runs: list[CrawlRunRead] = []


class SourceHealthSummary(BaseModel):
    total_sources: int
    active_sources: int
    healthy_sources: int
    warning_sources: int
    failed_sources: int
    never_crawled_sources: int
    disabled_sources: int


class SourceHealthListResponse(BaseModel):
    summary: SourceHealthSummary
    items: list[SourceHealthRead]


class SourceCrawlRunListResponse(BaseModel):
    items: list[CrawlRunRead]


class CrawlCandidateListResponse(BaseModel):
    items: list[CrawlCandidateRead]
    total: int
    skip: int
    limit: int


class CrawlCandidateCountRead(BaseModel):
    code: str | None
    label: str
    count: int


class CrawlCandidateStatisticsResponse(BaseModel):
    total: int
    by_status: list[CrawlCandidateCountRead]
    by_skip_reason: list[CrawlCandidateCountRead]
    by_content_kind: list[CrawlCandidateCountRead]


class ThinkTankDetailRead(ThinkTankRead):
    sources: list[SourceRead] = []
