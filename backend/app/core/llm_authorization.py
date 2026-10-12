import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum


class LLMScope(StrEnum):
    relevance_sample = "relevance_sample"
    report_generation = "report_generation"


class LLMNotAuthorized(RuntimeError):
    """A policy denial, not a model failure and never an automatic retry."""


def document_hash(title: str, content: str) -> str:
    payload = json.dumps([title, content], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def candidate_target_key(source_id: int, normalized_url: str) -> str:
    value = json.dumps([source_id, normalized_url], separators=(",", ":"))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LLMContext:
    scope: LLMScope
    target_key: str
    document_hash: str
    report_id: int | None = None


@dataclass(frozen=True)
class LLMPermit:
    authorization_id: int
    context: LLMContext


def report_context(report) -> LLMContext:
    if not report.content:
        raise LLMNotAuthorized("报告正文为空，不能授权外发。")
    return LLMContext(
        scope=LLMScope.report_generation,
        target_key=str(report.id),
        document_hash=document_hash(report.title or "", report.content),
        report_id=report.id,
    )
