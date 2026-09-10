from datetime import datetime
from io import BytesIO
from types import SimpleNamespace

from docx import Document

from app.services.report_export_service import (
    build_report_docx,
    build_report_markdown,
)


def _sample_report():
    return SimpleNamespace(
        id=1,
        title="Sample China Report",
        url="https://example.com/report",
        pdf_url="https://example.com/report.pdf",
        published_at=datetime(2026, 1, 2, 3, 4, 5),
        ai_generated_at=datetime(2026, 1, 3, 4, 5, 6),
        summary="观点摘要正文。",
        commentary="分析评论正文。",
        translation="全文翻译正文。",
        content="Original content.",
    )


def _sample_web_article():
    return SimpleNamespace(
        id=2,
        title="Sample Brookings Web Article",
        url="https://www.brookings.edu/articles/china-policy/",
        pdf_url=None,
        page_count=None,
        published_at=datetime(2026, 9, 9, 10, 0, 0),
        ai_generated_at=datetime(2026, 9, 10, 11, 0, 0),
        summary="观点摘要正文。",
        commentary="分析评论正文。",
        translation="全文翻译正文。",
        content="Original web article content.",
    )


def test_build_report_markdown_contains_all_sections():
    markdown = build_report_markdown(_sample_report())

    assert "# Sample China Report" in markdown
    assert "## 基本信息" in markdown
    assert "- 原文类型：PDF 报告" in markdown
    assert "- PDF 链接：https://example.com/report.pdf" in markdown
    assert "## 观点摘要" in markdown
    assert "## 分析评论" in markdown
    assert "## 全文翻译" in markdown
    assert "## 原文正文" in markdown


def test_build_report_markdown_marks_web_article_metadata():
    markdown = build_report_markdown(_sample_web_article())

    assert "- 原文类型：网页长文" in markdown
    assert "- 原文链接：https://www.brookings.edu/articles/china-policy/" in markdown
    assert "- PDF：不适用" in markdown
    assert "PDF 链接" not in markdown


def test_build_report_docx_contains_formal_sections():
    docx_bytes = build_report_docx(_sample_report())
    document = Document(BytesIO(docx_bytes))
    paragraphs = [
        paragraph.text
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]

    assert paragraphs[0] == "Sample China Report"
    assert "智库报告翻译与分析成果" in paragraphs
    assert "目录" in paragraphs
    assert "观点摘要" in paragraphs
    assert "分析评论" in paragraphs
    assert "全文翻译" in paragraphs
    assert "原文正文" in paragraphs
    assert len(document.tables) == 1


def test_build_report_docx_marks_web_article_metadata():
    docx_bytes = build_report_docx(_sample_web_article())
    document = Document(BytesIO(docx_bytes))
    table = document.tables[0]
    rows = [(row.cells[0].text, row.cells[1].text) for row in table.rows]

    assert ("原文类型", "网页长文") in rows
    assert ("PDF", "不适用") in rows
    assert not any(label == "PDF 链接" for label, _ in rows)
