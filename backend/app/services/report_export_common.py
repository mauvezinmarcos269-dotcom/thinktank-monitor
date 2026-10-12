from __future__ import annotations

from typing import Any

from app.core.content_kind import ReportContentKind, get_content_kind_label
from app.core.status import get_report_review_status_label


def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    return value.replace("\r\n", "\n").strip()


def is_pdf_report(report: Any) -> bool:
    content_kind = normalize_text(getattr(report, "content_kind", ""))

    if content_kind == ReportContentKind.pdf.value:
        return True

    if content_kind == ReportContentKind.web_article.value:
        return False

    return bool(
        normalize_text(getattr(report, "pdf_url", ""))
        or getattr(report, "page_count", None)
    )


def build_metadata_items(report: Any) -> list[tuple[str, str]]:
    report_id = getattr(report, "id", None)
    source_url = normalize_text(getattr(report, "url", ""))
    pdf_url = normalize_text(getattr(report, "pdf_url", ""))
    published_at = getattr(report, "published_at", None)
    ai_generated_at = getattr(report, "ai_generated_at", None)
    content_kind = normalize_text(getattr(report, "content_kind", ""))
    review_status = normalize_text(getattr(report, "review_status", ""))
    review_note = normalize_text(getattr(report, "review_note", None))
    reviewed_at = getattr(report, "reviewed_at", None)
    document_type = get_content_kind_label(
        content_kind
        if content_kind in {
            ReportContentKind.pdf.value,
            ReportContentKind.web_article.value,
        }
        else (
            ReportContentKind.pdf.value
            if is_pdf_report(report)
            else ReportContentKind.web_article.value
        )
    )
    content = normalize_text(getattr(report, "content", None))
    translation = normalize_text(getattr(report, "translation", None))
    # summary 是历史字段名，导出中按业务语义展示为“主要观点”。
    summary = normalize_text(getattr(report, "summary", None))
    commentary = normalize_text(getattr(report, "commentary", None))

    metadata = [
        ("报告 ID", str(report_id or "未知")),
        ("原文类型", document_type),
        ("复核状态", get_report_review_status_label(review_status)),
        ("复核时间", str(reviewed_at or "未知")),
        ("复核意见", review_note or "暂无"),
        ("原文链接", source_url or "暂无"),
    ]

    if is_pdf_report(report):
        metadata.append(("PDF 链接", pdf_url or "暂无"))
    else:
        metadata.append(("PDF", "不适用"))

    metadata.extend(
        [
            ("发布时间", str(published_at or "未知")),
            ("AI 生成时间", str(ai_generated_at or "未知")),
            ("原文字数", f"{len(content)} 字符" if content else "暂无"),
            (
                "翻译字数",
                f"{len(translation)} 字符" if translation else "暂无",
            ),
            ("主要观点字数", f"{len(summary)} 字符" if summary else "暂无"),
            (
                "深层研判字数",
                f"{len(commentary)} 字符" if commentary else "暂无",
            ),
        ]
    )

    return metadata


def build_export_filename(
    report_id: int,
    title: str | None,
    extension: str,
) -> str:
    base = normalize_text(title) or f"report-{report_id}"
    safe = "".join(
        char
        if char.isalnum() or char in {" ", "-", "_"}
        else "_"
        for char in base
    ).strip()
    safe = "_".join(safe.split())

    if not safe:
        safe = f"report-{report_id}"

    return f"{report_id}-{safe[:80]}-ai-results.{extension}"
