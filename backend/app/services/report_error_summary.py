import re
from typing import Literal

ReportProcessingOperation = Literal["ai", "fetch"]

_SUMMARY_MAX_LENGTH = 180
_AI_FIELD_LABELS = {
    "translation": "翻译稿",
    "summary": "摘要稿",
    "commentary": "评论稿",
}


def _truncate(text: str) -> str:
    if len(text) <= _SUMMARY_MAX_LENGTH:
        return text

    return f"{text[: _SUMMARY_MAX_LENGTH - 1].rstrip()}…"


def _strip_exception_prefixes(text: str) -> str:
    prefixes = (
        "报告最终摘要/评论生成失败:",
        "报告最终摘要/评论生成失败：",
        "全文翻译生成失败:",
        "全文翻译生成失败：",
        "全文摘要生成失败:",
        "全文摘要生成失败：",
        "全文评论生成失败:",
        "全文评论生成失败：",
        "ValueError:",
        "RuntimeError:",
        "ReportDocumentValidationError:",
    )

    current = text.strip()
    changed = True
    while changed:
        changed = False
        for prefix in prefixes:
            if current.startswith(prefix):
                current = current[len(prefix) :].strip()
                changed = True
                break

    return current


def summarize_report_processing_error(
    text: str | None,
    *,
    operation: ReportProcessingOperation,
) -> str:
    if not text or not text.strip():
        return "未记录具体失败原因。"

    compact = re.sub(r"\s+", " ", text).strip()
    sql_details_index = re.search(r"\s+\[(?:SQL|parameters):", compact, re.IGNORECASE)
    summary_source = compact[: sql_details_index.start()].rstrip() if sql_details_index else compact

    length_error = re.search(
        r"\b(translation|summary|commentary)\s+长度(不足|超出):\s*"
        r"期望(至少|不超过)\s*(\d+)\s*字符，实际为\s*(\d+)\s*字符",
        summary_source,
        re.IGNORECASE,
    )
    if operation == "ai" and length_error:
        field, status, expectation, expected, actual = length_error.groups()
        label = _AI_FIELD_LABELS[field.lower()]
        return f"AI {label}长度{status}：要求{expectation} {expected} 字，实际 {actual} 字。"

    http_status = re.search(
        r"(?:HTTPStatusError:\s*)?(?:Client|Server) error [\"'](\d{3})\s+[^\"']+[\"']",
        summary_source,
        re.IGNORECASE,
    )
    if http_status:
        subject = "AI 服务" if operation == "ai" else "报告正文地址"
        return f"{subject}请求失败：返回 HTTP {http_status.group(1)}。"

    if re.search(r"Timeout(?:Exception|Error)|ReadTimeout|ConnectTimeout", summary_source, re.IGNORECASE):
        return "AI 服务响应超时，请稍后重试。" if operation == "ai" else "报告正文获取超时，请稍后重试。"

    if re.search(r"ConnectError|ConnectException", summary_source, re.IGNORECASE):
        return "无法连接 AI 服务，请检查服务配置和网络。" if operation == "ai" else "无法连接报告正文地址。"

    if operation == "ai":
        if "LLM_API_KEY 未配置" in summary_source:
            return "AI 服务配置不完整：缺少 API 密钥。"
        if "LLM_BASE_URL 未配置" in summary_source:
            return "AI 服务配置不完整：缺少服务地址。"
        if "LLM_MODEL 未配置" in summary_source:
            return "AI 服务配置不完整：缺少模型名称。"
        if "外发总开关已关闭" in summary_source:
            return "AI 处理未执行：外发总开关已关闭。"
        if "未授权" in summary_source or "缺少授权" in summary_source:
            return "AI 处理未执行：当前文档尚未获得相应用途授权。"
        if "不是有效 JSON" in summary_source or "返回格式异常" in summary_source:
            return "AI 返回格式异常：未获得有效的结构化内容。"
        if "LLM 返回为空" in summary_source or "最终摘要不能为空" in summary_source:
            return "AI 未返回有效摘要内容。"
        if "最终评论不能为空" in summary_source:
            return "AI 未返回有效评论内容。"
        if "最终翻译不能为空" in summary_source:
            return "AI 未返回有效翻译内容。"

    stripped = _strip_exception_prefixes(summary_source)
    if stripped:
        return _truncate(stripped)

    return "AI 处理失败，请查看任务日志。" if operation == "ai" else "报告正文获取失败，请查看任务日志。"
