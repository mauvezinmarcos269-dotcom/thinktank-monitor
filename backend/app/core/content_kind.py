from enum import StrEnum


class ReportContentKind(StrEnum):
    pdf = "pdf"
    web_article = "web_article"


CONTENT_KIND_LABELS = {
    ReportContentKind.pdf.value: "PDF 报告",
    ReportContentKind.web_article.value: "网页长文",
}


def get_content_kind_label(value: str | None) -> str:
    if not value:
        return "未知类型"

    return CONTENT_KIND_LABELS.get(value, value)
