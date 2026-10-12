from __future__ import annotations

from app.core.status import CrawlCandidateSkipReason

DOCUMENT_FAILED_LABEL = "PDF 获取或页数/文本检查失败"
MISSING_PDF_LABEL = "未发现 PDF 链接"
SHORT_PDF_LABEL = "PDF 页数不足"
PDF_TEXT_EMPTY_LABEL = "PDF 文本不足"
PDF_PARSE_FAILED_LABEL = "PDF 获取或解析失败"

DOCUMENT_FAILURE_LABEL_ORDER = (
    MISSING_PDF_LABEL,
    SHORT_PDF_LABEL,
    PDF_TEXT_EMPTY_LABEL,
    PDF_PARSE_FAILED_LABEL,
    DOCUMENT_FAILED_LABEL,
)

SKIP_REASON_LABELS = {
    CrawlCandidateSkipReason.invalid_url.value: "无效 URL",
    CrawlCandidateSkipReason.duplicate_in_feed.value: "同一来源内重复",
    CrawlCandidateSkipReason.duplicate_existing.value: "已入库重复",
    CrawlCandidateSkipReason.duplicate_pending.value: "已有待授权候选",
    CrawlCandidateSkipReason.document_failed.value: DOCUMENT_FAILED_LABEL,
    CrawlCandidateSkipReason.relevance_failed.value: "涉华判断失败",
    CrawlCandidateSkipReason.non_china_related.value: "非涉华",
    CrawlCandidateSkipReason.concurrent_duplicate.value: "并发重复入库",
}

DOCUMENT_FAILURE_LABELS = set(DOCUMENT_FAILURE_LABEL_ORDER)


def classify_document_failure_label(error: object | None) -> str:
    text = str(error or "")
    normalized = text.casefold()

    if "报告详情页中未发现 pdf 链接" in normalized or "未发现 pdf 链接" in normalized:
        return MISSING_PDF_LABEL

    if "报告页数不足" in text or "minimum_page_count" in normalized:
        return SHORT_PDF_LABEL

    if "未提取出有效文本" in text:
        return PDF_TEXT_EMPTY_LABEL

    parse_markers = (
        "没有返回 pdf 内容",
        "不是有效的 pdf",
        "无法打开 pdf",
        "pdf 文本提取失败",
    )
    if any(marker in normalized for marker in parse_markers):
        return PDF_PARSE_FAILED_LABEL

    return DOCUMENT_FAILED_LABEL


def get_skip_reason_label(
    code: str | None,
    *,
    error: object | None = None,
    stored_label: str | None = None,
) -> str:
    if code == CrawlCandidateSkipReason.document_failed.value:
        label = classify_document_failure_label(error)

        if label != DOCUMENT_FAILED_LABEL:
            return label

        if stored_label in DOCUMENT_FAILURE_LABELS:
            return stored_label

    if stored_label:
        return stored_label

    if code is None:
        return ""

    return SKIP_REASON_LABELS.get(code, code)
