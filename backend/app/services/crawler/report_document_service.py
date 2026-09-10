from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from app.services.crawler.content_extractor import (
    extract_article_content,
    extract_report_pdf_url,
)
from app.services.crawler.http_client import (
    FetchResult,
    fetch_resource,
)
from app.services.crawler.pdf_extractor import extract_pdf_text

MIN_REPORT_PAGE_COUNT = 20
MIN_WEB_ARTICLE_CONTENT_LENGTH = 3000


@dataclass(frozen=True)
class ReportDocumentResult:
    """完整研究报告抓取结果。"""

    page_url: str
    pdf_url: str | None
    text: str
    page_count: int | None
    non_empty_page_count: int | None
    pdf_byte_length: int | None
    content_kind: str = "pdf"


def _looks_like_pdf(resource: FetchResult) -> bool:
    """
    判断 HTTP 响应是否为 PDF。

    同时参考 Content-Type 和最终 URL，
    避免个别网站 Content-Type 配置不规范。
    """
    content_type = resource.content_type.lower()

    if "application/pdf" in content_type:
        return True

    path = urlsplit(resource.final_url).path.lower()

    return path.endswith(".pdf")


async def fetch_report_document(
    url: str,
    minimum_page_count: int = MIN_REPORT_PAGE_COUNT,
    allow_web_article_fallback: bool = False,
    minimum_web_content_length: int = MIN_WEB_ARTICLE_CONTENT_LENGTH,
) -> ReportDocumentResult:
    """
    获取研究报告 PDF 并提取全文。

    支持两种入口：
    1. 报告详情页 URL；
    2. PDF 直链。

    报告页会先寻找 PDF 地址，再下载 PDF。
    PDF 页数低于 minimum_page_count 时拒绝继续处理。
    """
    if minimum_page_count <= 0:
        raise ValueError(
            "minimum_page_count 必须大于 0。"
        )

    if minimum_web_content_length <= 0:
        raise ValueError(
            "minimum_web_content_length 必须大于 0。"
        )

    resource = await fetch_resource(url)

    page_url = resource.final_url

    # ------------------------------------------------------------
    # 情况一：传入的 URL 本身就是 PDF
    # ------------------------------------------------------------
    if _looks_like_pdf(resource):
        pdf_resource = resource
        pdf_url = resource.final_url

    # ------------------------------------------------------------
    # 情况二：传入的是报告详情页
    # ------------------------------------------------------------
    else:
        pdf_url = extract_report_pdf_url(
            resource.content,
            page_url,
        )

        if pdf_url is None:
            if allow_web_article_fallback:
                content = extract_article_content(
                    resource.content
                )

                if (
                    content
                    and len(content)
                    >= minimum_web_content_length
                ):
                    return ReportDocumentResult(
                        page_url=page_url,
                        pdf_url=None,
                        text=content,
                        page_count=None,
                        non_empty_page_count=None,
                        pdf_byte_length=None,
                        content_kind="web_article",
                    )

            raise ValueError(
                "报告详情页中未发现 PDF 链接。"
            )

        pdf_resource = await fetch_resource(pdf_url)

        if not _looks_like_pdf(pdf_resource):
            raise ValueError(
                "发现的报告链接没有返回 PDF 内容。"
            )

        pdf_url = pdf_resource.final_url

    # 部分服务器可能错误返回 HTML，
    # 再检查一次 PDF 文件头，降低误判概率。
    if not pdf_resource.content.startswith(b"%PDF"):
        raise ValueError(
            "下载内容不是有效的 PDF 文件。"
        )

    extraction = extract_pdf_text(
        pdf_resource.content
    )

    if extraction.page_count < minimum_page_count:
        raise ValueError(
            "报告页数不足："
            f"{extraction.page_count} 页，"
            f"要求至少 {minimum_page_count} 页。"
        )

    if not extraction.text:
        raise ValueError(
            "PDF 未提取出有效文本。"
        )

    return ReportDocumentResult(
        page_url=page_url,
        pdf_url=pdf_url,
        text=extraction.text,
        page_count=extraction.page_count,
        non_empty_page_count=(
            extraction.non_empty_page_count
        ),
        pdf_byte_length=len(
            pdf_resource.content
        ),
    )
