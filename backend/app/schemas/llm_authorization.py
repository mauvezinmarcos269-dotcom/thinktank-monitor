from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.llm_authorization import LLMScope


class LLMAuthorizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: LLMScope
    target_id: int = Field(gt=0)
    document_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    provider: str = Field(min_length=1, max_length=100)
    endpoint: str = Field(min_length=1, max_length=2000)
    model: str = Field(min_length=1, max_length=200)
    policy_version: Literal[1]
    consent: Literal["allow_external_processing"]


class LLMAuthorizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scope: LLMScope
    target_key: str
    document_hash: str
    policy_version: int
    provider: str
    endpoint: str
    model: str
    candidate_id: int | None
    report_id: int | None
    granted_by: int | None
    granted_at: datetime
    revoked_by: int | None
    revoked_at: datetime | None


class LLMAuthorizationPreview(BaseModel):
    scope: LLMScope
    target_id: int
    title: str
    document_hash: str
    content_length: int
    data_scope: str
    provider: str
    endpoint: str
    model: str
    policy_version: int
    outbound_enabled: bool
    authorized: bool
