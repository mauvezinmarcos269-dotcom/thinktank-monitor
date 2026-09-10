from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CrawlQualityStats:
    raw_candidates: int = 0
    unique_candidates: int = 0
    saved_reports: int = 0
    invalid_url: int = 0
    duplicate_in_feed: int = 0
    duplicate_existing: int = 0
    document_failed: int = 0
    relevance_failed: int = 0
    non_china_related: int = 0
    concurrent_duplicate: int = 0
    samples: list[str] = field(default_factory=list)

    def add_sample(self, reason: str, url: object, detail: object | None = None) -> None:
        if len(self.samples) >= 5:
            return

        text = f"{reason}: {url}"

        if detail:
            text = f"{text} ({str(detail)[:160]})"

        self.samples.append(text[:500])

    def to_summary(self) -> str | None:
        parts = [
            f"原始候选 {self.raw_candidates} 条",
            f"有效去重后 {self.unique_candidates} 条",
            f"入库 {self.saved_reports} 条",
        ]

        skip_parts = []

        if self.invalid_url:
            skip_parts.append(f"无效 URL {self.invalid_url} 条")
        if self.duplicate_in_feed:
            skip_parts.append(f"同一来源内重复 {self.duplicate_in_feed} 条")
        if self.duplicate_existing:
            skip_parts.append(f"已入库重复 {self.duplicate_existing} 条")
        if self.document_failed:
            skip_parts.append(f"PDF 获取或页数/文本检查失败 {self.document_failed} 条")
        if self.relevance_failed:
            skip_parts.append(f"涉华判断失败 {self.relevance_failed} 条")
        if self.non_china_related:
            skip_parts.append(f"非涉华 {self.non_china_related} 条")
        if self.concurrent_duplicate:
            skip_parts.append(f"并发重复入库 {self.concurrent_duplicate} 条")

        if skip_parts:
            parts.append("跳过：" + "，".join(skip_parts))

        if self.samples:
            parts.append("样例：" + "；".join(self.samples))

        if not skip_parts and not self.samples:
            return None

        return "质量检查：" + "；".join(parts)
