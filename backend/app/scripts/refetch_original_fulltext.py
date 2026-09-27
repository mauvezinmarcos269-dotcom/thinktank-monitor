from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from app.core.status import ReportAIStatus, ReportCrawlStatus, ReportReviewStatus
from app.db.session import AsyncSessionLocal
from app.models.report import Report
from app.services.crawler.candidate_intake import normalize_url
from app.services.crawler.content_extractor import extract_article_content
from app.services.crawler.http_client import fetch_resource
from app.utils.datetime import utc_now_naive

DEFAULT_MIN_CONTENT_LENGTH = 3000


@dataclass(frozen=True)
class OriginalLinkCandidate:
    url: str
    label: str
    score: int


def _hostname(url: str) -> str:
    return urlsplit(url).hostname or ""


def find_original_fulltext_links(
    html: str | bytes,
    base_url: str,
    *,
    preferred_domains: set[str] | None = None,
) -> list[OriginalLinkCandidate]:
    soup = BeautifulSoup(html, "html.parser")
    base_host = _hostname(base_url).lower()
    candidates: list[OriginalLinkCandidate] = []

    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href", "")).strip()
        if not href:
            continue

        absolute_url = urljoin(base_url, href)
        parsed = urlsplit(absolute_url)
        if parsed.scheme not in {"http", "https"}:
            continue

        host = (parsed.hostname or "").lower()
        label = " ".join(anchor.stripped_strings).strip()
        label_lower = label.lower()
        url_lower = absolute_url.lower()

        score = 0
        if "continue reading" in label_lower:
            score += 20
        if "read the full" in label_lower or "full text" in label_lower:
            score += 12
        if "original" in label_lower:
            score += 8
        if " at " in f" {label_lower} ":
            score += 3
        if host and host != base_host:
            score += 5
        if preferred_domains and any(domain in host for domain in preferred_domains):
            score += 10
        if preferred_domains and any(domain in url_lower for domain in preferred_domains):
            score += 5

        if score <= 0:
            continue

        candidates.append(
            OriginalLinkCandidate(
                url=absolute_url,
                label=label,
                score=score,
            )
        )

    candidates.sort(
        key=lambda candidate: (
            candidate.score,
            len(candidate.label),
        ),
        reverse=True,
    )
    return candidates


async def _fetch_original_text(
    original_url: str,
    *,
    minimum_content_length: int,
) -> tuple[str, str]:
    resource = await fetch_resource(original_url)
    text = extract_article_content(resource.content)

    if not text or len(text) < minimum_content_length:
        raise ValueError(
            "原始页面正文不足："
            f"{len(text or '')} 字符，"
            f"要求至少 {minimum_content_length} 字符。"
        )

    return resource.final_url, text


async def refetch_original_fulltext(
    *,
    report_id: int,
    original_url: str | None,
    preferred_domains: set[str],
    minimum_content_length: int,
    apply: bool,
    update_report_url: bool,
) -> dict[str, object]:
    async with AsyncSessionLocal() as db:
        report = await db.get(Report, report_id)
        if report is None:
            return {
                "status": "not_found",
                "report_id": report_id,
            }

        old_content_length = len(report.content or "")
        discovery_candidates: list[OriginalLinkCandidate] = []

        if original_url is None:
            resource = await fetch_resource(report.url)
            discovery_candidates = find_original_fulltext_links(
                resource.content,
                resource.final_url,
                preferred_domains=preferred_domains,
            )
            if not discovery_candidates:
                return {
                    "status": "original_link_not_found",
                    "report_id": report.id,
                    "report_url": report.url,
                    "old_content_length": old_content_length,
                }
            original_url = discovery_candidates[0].url

        final_url, original_text = await _fetch_original_text(
            original_url,
            minimum_content_length=minimum_content_length,
        )
        new_content_length = len(original_text)

        result: dict[str, object] = {
            "status": "dry_run",
            "report_id": report.id,
            "title": report.title,
            "report_url": report.url,
            "original_url": original_url,
            "final_original_url": final_url,
            "old_content_length": old_content_length,
            "new_content_length": new_content_length,
            "content_gain": new_content_length - old_content_length,
            "candidates": [
                {
                    "url": candidate.url,
                    "label": candidate.label,
                    "score": candidate.score,
                }
                for candidate in discovery_candidates[:5]
            ],
            "would_update_report_url": update_report_url,
        }

        if not apply:
            return result

        now = utc_now_naive()
        report.content = original_text
        report.content_hash = hashlib.sha256(
            original_text.encode("utf-8")
        ).hexdigest()
        report.content_fetched_at = now
        report.crawl_status = ReportCrawlStatus.success.value
        report.crawl_error = None
        report.translation = None
        report.summary = None
        report.commentary = None
        report.ai_status = ReportAIStatus.pending.value
        report.ai_retry_count = 0
        report.ai_generated_at = None
        report.review_status = ReportReviewStatus.pending_review.value
        report.review_note = (
            "已补抓原始全文，旧 AI 成果已清空，待重新生成并复核。"
        )
        report.updated_at = now

        if update_report_url:
            report.url = final_url
            report.normalized_url = normalize_url(final_url)

        await db.commit()

        result["status"] = "updated"
        result["new_ai_status"] = report.ai_status
        result["new_review_status"] = report.review_status
        result["updated_report_url"] = report.url
        result["new_content_hash"] = report.content_hash
        return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "尝试从转载/导流报告页识别原始全文链接，提取更完整正文。"
            "默认 dry-run；只有传入 --apply 才会更新数据库。"
        )
    )
    parser.add_argument(
        "report_id",
        type=int,
        help="需要补抓原始全文的报告 ID。",
    )
    parser.add_argument(
        "--original-url",
        help="手动指定原始全文 URL；不传则从报告当前 URL 页面自动识别。",
    )
    parser.add_argument(
        "--preferred-domain",
        action="append",
        default=[],
        help="优先匹配的原始来源域名片段，可重复传入。",
    )
    parser.add_argument(
        "--min-content-length",
        type=int,
        default=DEFAULT_MIN_CONTENT_LENGTH,
        help=f"原始全文最小正文长度，默认 {DEFAULT_MIN_CONTENT_LENGTH}。",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="实际覆盖报告正文，并清空旧 AI 成果。",
    )
    parser.add_argument(
        "--update-report-url",
        action="store_true",
        help="同时把报告 URL 更新为原始全文最终 URL。",
    )
    return parser.parse_args()


async def main_async() -> int:
    args = parse_args()
    result = await refetch_original_fulltext(
        report_id=args.report_id,
        original_url=args.original_url,
        preferred_domains={domain.lower() for domain in args.preferred_domain},
        minimum_content_length=args.min_content_length,
        apply=args.apply,
        update_report_url=args.update_report_url,
    )
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )
    return 1 if result["status"] == "not_found" else 0


def main() -> None:
    raise SystemExit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
