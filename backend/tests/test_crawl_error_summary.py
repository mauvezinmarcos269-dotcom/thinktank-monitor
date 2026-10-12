import pytest

from app.services.crawl_error_summary import summarize_crawl_error


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            "ProgrammingError: <class "
            "'asyncpg.exceptions.UndefinedColumnError'>: "
            'column "document_hash" of relation "crawl_candidates" does not exist '
            "[SQL: INSERT INTO crawl_candidates]",
            "数据库结构未同步：数据表 crawl_candidates 缺少字段 document_hash。",
        ),
        (
            "HTTPStatusError: Client error '404 Not Found' for url "
            "'https://www.rand.org/rss.xml'",
            "来源访问失败：目标网站返回 HTTP 404。",
        ),
        (
            "ValueError: 所有发现入口抓取失败：https://example.org/ "
            "(ConnectError: )",
            "来源连接失败：所有发现入口均无法访问。",
        ),
        (
            "ConnectError: ",
            "来源连接失败：无法连接目标网站。",
        ),
        (
            "TimeoutError: ",
            "来源访问超时：目标网站未在限定时间内响应。",
        ),
        (
            "ValueError: RSS 解析失败: <unknown>:58:0: undefined entity",
            "RSS 解析失败：订阅内容包含无法识别的格式。",
        ),
        (
            "ValueError: 当前尚未配置该 website 来源的专用解析器："
            "https://www.example.org/",
            "来源尚未适配：未配置该网站的专用解析器"
            "（https://www.example.org/）。",
        ),
    ],
)
def test_summarize_crawl_error_known_patterns(error: str, expected: str):
    assert summarize_crawl_error(error) == expected


def test_summarize_crawl_error_keeps_unknown_error_bounded():
    error = "UnknownFailure: " + "x" * 500

    summary = summarize_crawl_error(error)

    assert len(summary) == 180
    assert summary.endswith("…")
    assert "x" in summary
