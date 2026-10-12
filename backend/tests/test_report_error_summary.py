import pytest

from app.services.report_error_summary import summarize_report_processing_error


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            "报告最终摘要/评论生成失败: ValueError: 全文评论生成失败: "
            "ValueError: commentary 长度不足: 期望至少 2000 字符，实际为 1701 字符",
            "AI 评论稿长度不足：要求至少 2000 字，实际 1701 字。",
        ),
        (
            "ValueError: summary 长度超出: 期望不超过 2200 字符，实际为 2552 字符",
            "AI 摘要稿长度超出：要求不超过 2200 字，实际 2552 字。",
        ),
        ("ValueError: LLM_API_KEY 未配置", "AI 服务配置不完整：缺少 API 密钥。"),
        ("httpx.ReadTimeout", "AI 服务响应超时，请稍后重试。"),
        ("ValueError: LLM 返回的内容不是有效 JSON", "AI 返回格式异常：未获得有效的结构化内容。"),
    ],
)
def test_summarize_ai_processing_error(error: str, expected: str) -> None:
    assert summarize_report_processing_error(error, operation="ai") == expected


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        ("ValueError: 报告详情页中未发现 PDF 链接。", "报告详情页中未发现 PDF 链接。"),
        ("TimeoutError:", "报告正文获取超时，请稍后重试。"),
        (
            "HTTPStatusError: Client error '404 Not Found' for url 'https://example.org/report.pdf'",
            "报告正文地址请求失败：返回 HTTP 404。",
        ),
        (
            "Client error '403 Forbidden' for url 'https://example.org/report'\n"
            "For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/403",
            "报告正文地址请求失败：返回 HTTP 403。",
        ),
    ],
)
def test_summarize_report_fetch_error(error: str, expected: str) -> None:
    assert summarize_report_processing_error(error, operation="fetch") == expected


def test_unknown_processing_error_is_bounded() -> None:
    summary = summarize_report_processing_error("x" * 500, operation="ai")

    assert len(summary) == 180
    assert summary.endswith("…")
