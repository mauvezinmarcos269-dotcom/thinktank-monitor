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


def _classify_success_without_reports(error_text: str | None) -> SourceDiagnosis:
    text = error_text or ""

    if "原始候选 0 条" in text:
        return SourceDiagnosis(
            code="no_candidates",
            label="未发现候选报告",
            advice="抓取成功但未解析出候选条目，请检查来源入口、列表页结构或是否需要新增发现入口。",
        )

    if "PDF 获取或页数/文本检查失败" in text:
        return SourceDiagnosis(
            code="document_gate_failed",
            label="候选未通过文档检查",
            advice="抓取成功但候选未通过 PDF 获取、页数或文本检查，请查看候选样例中的链接、页数和错误摘要。",
        )

    if "涉华判断失败" in text:
        return SourceDiagnosis(
            code="relevance_gate_failed",
            label="涉华判断失败",
            advice="抓取成功但 AI 涉华判断失败，请检查模型配置、队列和候选正文。",
        )

    if "非涉华" in text:
        return SourceDiagnosis(
            code="non_china_candidates",
            label="候选未通过涉华判断",
            advice="抓取成功但候选被判定为非涉华；如疑似误判，请查看候选涉华判断说明。",
        )

    if "已入库重复" in text or "同一来源内重复" in text:
        return SourceDiagnosis(
            code="duplicate_candidates",
            label="候选均为重复",
            advice="抓取成功但候选已重复或已入库，通常无需处理；可查看候选列表确认是否有新增报告。",
        )

    return SourceDiagnosis(
        code="no_reports_saved",
        label="暂无入库报告",
        advice="抓取成功但未保存报告，可能是无新增、重复、非涉华或报告不满足页数要求。",
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
        return _classify_success_without_reports(error_text)

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
