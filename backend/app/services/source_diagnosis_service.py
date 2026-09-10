from __future__ import annotations

from dataclasses import dataclass

from app.models.source import CrawlStatusEnum


@dataclass(frozen=True)
class SourceDiagnosis:
    code: str
    label: str
    advice: str


DEFAULT_DIAGNOSIS = SourceDiagnosis(
    code="unknown",
    label="未知问题",
    advice="查看原始错误信息，并人工确认该来源页面结构是否变化。",
)


def classify_source_diagnosis(
    *,
    crawl_status: CrawlStatusEnum | str,
    error_text: str | None,
    saved_report_count: int,
) -> SourceDiagnosis:
    text = (error_text or "").casefold()

    if crawl_status == CrawlStatusEnum.never:
        return SourceDiagnosis(
            code="not_crawled",
            label="尚未抓取",
            advice="可先手动抓取一次，确认该来源是否可用。",
        )

    if crawl_status == CrawlStatusEnum.running:
        return SourceDiagnosis(
            code="running",
            label="抓取中",
            advice="等待当前任务完成后再判断状态。",
        )

    if crawl_status == CrawlStatusEnum.success and saved_report_count == 0:
        return SourceDiagnosis(
            code="no_reports_saved",
            label="暂无入库报告",
            advice="抓取成功但未保存报告，可能是无新增、重复、非涉华或报告不满足页数要求。",
        )

    if crawl_status == CrawlStatusEnum.success:
        return SourceDiagnosis(
            code="ok",
            label="正常",
            advice="该来源最近抓取正常。",
        )

    if not text:
        return DEFAULT_DIAGNOSIS

    network_markers = (
        "timeout",
        "timed out",
        "connecterror",
        "network",
        "connection",
        "connection refused",
        "connect call failed",
        "readerror",
        "remote protocol",
        "nodename nor servname",
        "name or service not known",
    )
    if any(marker in text for marker in network_markers):
        return SourceDiagnosis(
            code="network",
            label="网络连接问题",
            advice="检查目标网站连通性、DNS、代理和抓取超时设置。",
        )

    http_markers = (
        "httpstatuserror",
        "client error",
        "server error",
        "response status code",
        "403",
        "404",
        "429",
        "500",
        "502",
        "503",
        "504",
    )
    if any(marker in text for marker in http_markers):
        return SourceDiagnosis(
            code="http_status",
            label="HTTP 状态异常",
            advice="检查是否被目标站点拒绝、限流、页面迁移或服务端临时故障。",
        )

    if "报告页数不足" in (error_text or "") or "minimum_page_count" in text:
        return SourceDiagnosis(
            code="short_pdf",
            label="PDF 页数不足",
            advice="该文档可能不是长篇报告；当前规则要求一般不少于 20 页。",
        )

    pdf_markers = (
        "pdf",
        "不是有效的 pdf",
        "未提取出有效文本",
        "无法打开 pdf",
        "没有返回 pdf 内容",
        "未发现 pdf 链接",
    )
    if any(marker in text for marker in pdf_markers):
        return SourceDiagnosis(
            code="pdf_parse",
            label="PDF 获取或解析失败",
            advice="检查页面 PDF 链接、文件格式、扫描版 PDF 或反爬限制。",
        )

    parser_markers = (
        "专用解析器",
        "不支持此来源类型",
        "仅支持 rss 和 website",
        "parser",
        "parse",
    )
    if any(marker.casefold() in text for marker in parser_markers):
        return SourceDiagnosis(
            code="parser",
            label="解析规则缺失",
            advice="需要为该网站补充或更新专用解析器。",
        )

    ai_markers = (
        "ai",
        "celery enqueue failed",
        "llm",
        "siliconflow",
        "模型",
        "token",
    )
    if any(marker in text for marker in ai_markers):
        return SourceDiagnosis(
            code="ai_queue",
            label="AI 队列或模型问题",
            advice="检查 Celery worker、Redis 队列、模型 Key、模型超时和额度。",
        )

    return DEFAULT_DIAGNOSIS
