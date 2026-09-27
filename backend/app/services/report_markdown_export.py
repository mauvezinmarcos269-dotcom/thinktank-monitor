from __future__ import annotations

from typing import Any

from app.services.report_export_common import build_metadata_items, normalize_text


def build_report_markdown(report: Any) -> str:
    title = normalize_text(getattr(report, "title", None)) or "未命名报告"
    metadata = [
        f"- {label}：{value}"
        for label, value in build_metadata_items(report)
    ]

    sections = [
        f"# {title}",
        "",
        "## 基本信息",
        *metadata,
        "",
        "## 全文翻译稿",
        normalize_text(getattr(report, "translation", None)) or "暂无全文翻译。",
        "",
        "## 分析评论稿",
        "",
        "### 第一部分：主要观点",
        normalize_text(getattr(report, "summary", None))
        or "暂无主要观点，等待 AI 处理完成。",
        "",
        "### 第二部分：深层研判",
        normalize_text(getattr(report, "commentary", None))
        or "暂无深层研判，等待 AI 处理完成。",
        "",
        "## 原文正文",
        normalize_text(getattr(report, "content", None)) or "暂无原文正文。",
        "",
    ]

    return "\n".join(sections)
