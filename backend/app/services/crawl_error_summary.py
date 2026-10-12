import re

CRAWL_ERROR_SUMMARY_MAX_LENGTH = 180


def _truncate_summary(text: str) -> str:
    if len(text) <= CRAWL_ERROR_SUMMARY_MAX_LENGTH:
        return text
    return f"{text[: CRAWL_ERROR_SUMMARY_MAX_LENGTH - 1].rstrip()}…"


def summarize_crawl_error(text: str | None) -> str:
    if not text or not text.strip():
        return "无"

    compact = " ".join(text.split())
    summary_source = re.split(
        r"\s+\[(?:SQL|parameters):",
        compact,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].rstrip()

    undefined_column = re.search(
        r"UndefinedColumnError.*?column [\"']([^\"']+)[\"'] "
        r"of relation [\"']([^\"']+)[\"']",
        summary_source,
        flags=re.IGNORECASE,
    )
    if undefined_column:
        column, relation = undefined_column.groups()
        return f"数据库结构未同步：数据表 {relation} 缺少字段 {column}。"

    http_status = re.search(
        r"HTTPStatusError:.*?[\"'](\d{3})\s+[^\"']+[\"']",
        summary_source,
        flags=re.IGNORECASE,
    )
    if http_status:
        return f"来源访问失败：目标网站返回 HTTP {http_status.group(1)}。"

    if re.search(r"所有发现入口抓取失败", summary_source, flags=re.IGNORECASE):
        return "来源连接失败：所有发现入口均无法访问。"

    if re.search(r"ConnectError:", summary_source, flags=re.IGNORECASE):
        return "来源连接失败：无法连接目标网站。"

    if re.search(r"TimeoutError:", summary_source, flags=re.IGNORECASE):
        return "来源访问超时：目标网站未在限定时间内响应。"

    if re.search(r"RSS 解析失败", summary_source, flags=re.IGNORECASE):
        if re.search(r"undefined entity", summary_source, flags=re.IGNORECASE):
            return "RSS 解析失败：订阅内容包含无法识别的格式。"

        rss_reason = re.search(
            r"RSS 解析失败[:：]\s*(.+)$",
            summary_source,
            flags=re.IGNORECASE,
        )
        if rss_reason:
            return _truncate_summary(f"RSS 解析失败：{rss_reason.group(1)}")
        return "RSS 解析失败：订阅内容无法读取。"

    missing_parser = re.search(
        r"当前尚未配置该\s+website\s+来源的专用解析器[:：]\s*(\S+)",
        summary_source,
        flags=re.IGNORECASE,
    )
    if missing_parser:
        return (
            "来源尚未适配：未配置该网站的专用解析器"
            f"（{missing_parser.group(1)}）。"
        )

    if re.search(r"ProgrammingError:", summary_source, flags=re.IGNORECASE):
        return "数据库操作失败：请展开查看具体数据库异常。"

    if re.search(r"IntegrityError:", summary_source, flags=re.IGNORECASE):
        return "数据库写入失败：数据约束校验未通过。"

    if re.search(r"OperationalError:", summary_source, flags=re.IGNORECASE):
        return "数据库连接或执行失败：请检查数据库服务。"

    localized_value_error = re.match(
        r"^ValueError:\s*([\u3400-\u9fff].*)$",
        summary_source,
    )
    if localized_value_error:
        return _truncate_summary(localized_value_error.group(1))

    return _truncate_summary(summary_source)
