from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from statistics import median

import fitz
from ftfy import fix_text


@dataclass(frozen=True)
class PdfExtractionResult:
    """PDF 文本提取结果。"""

    text: str
    page_count: int
    non_empty_page_count: int


def _extract_page_text_in_reading_order(
    page: fitz.Page,
) -> tuple[str, str]:
    """按单栏或双栏页面的视觉阅读顺序提取文本。"""

    page_dict = page.get_text("dict")
    page_width = float(page.rect.width)
    page_height = float(page.rect.height)

    middle_x = page_width / 2.0
    gutter = max(18.0, page_width * 0.035)

    blocks: list[dict[str, object]] = []

    # 提取文本块，同时保留位置和字体大小信息。
    for raw_block in page_dict.get("blocks", []):
        if raw_block.get("type") != 0:
            continue

        line_texts: list[str] = []
        font_sizes: list[float] = []

        for line in raw_block.get("lines", []):
            parts: list[str] = []

            for span in line.get("spans", []):
                span_text = str(span.get("text", ""))

                if span_text:
                    parts.append(span_text)

                span_size = span.get("size")

                if (
                    isinstance(span_size, int | float)
                    and span_size > 0
                ):
                    font_sizes.append(float(span_size))

            line_text = "".join(parts).strip()

            if line_text:
                line_texts.append(line_text)

        text = "\n".join(line_texts).strip()

        if not text:
            continue

        x0, y0, x1, y1 = raw_block["bbox"]

        blocks.append(
            {
                "text": text,
                "x0": float(x0),
                "y0": float(y0),
                "x1": float(x1),
                "y1": float(y1),
                "font_size": (
                    median(font_sizes)
                    if font_sizes
                    else 0.0
                ),
            }
        )

    if not blocks:
        return "", ""

    # 用页面文本块的中位字体大小近似正文大小。
    visible_font_sizes = [
        float(block["font_size"])
        for block in blocks
        if float(block["font_size"]) > 0
    ]

    body_font_size = (
        median(visible_font_sizes)
        if visible_font_sizes
        else 0.0
    )

    footnotes: list[dict[str, object]] = []
    normal_blocks: list[dict[str, object]] = []

    # 页面的下半部分且字体明显小于正文时，优先视为脚注。
    for block in blocks:
        font_size = float(block["font_size"])
        y0 = float(block["y0"])

        is_footnote = (
            body_font_size > 0
            and y0 >= page_height * 0.55
            and font_size > 0
            and font_size <= body_font_size * 0.85
        )

        if is_footnote:
            footnotes.append(block)
        else:
            normal_blocks.append(block)

    full_width_blocks: list[dict[str, object]] = []
    column_blocks: list[dict[str, object]] = []

    # 区分跨栏文本块与普通栏文本块。
    for block in normal_blocks:
        x0 = float(block["x0"])
        x1 = float(block["x1"])
        block_width = x1 - x0

        spans_middle = (
            x0 < middle_x - gutter
            and x1 > middle_x + gutter
        )

        if (
            spans_middle
            or block_width >= page_width * 0.72
        ):
            full_width_blocks.append(block)
        else:
            column_blocks.append(block)

    left_blocks = [
        block
        for block in column_blocks
        if (
            float(block["x0"])
            + float(block["x1"])
        ) / 2.0 < middle_x
    ]

    right_blocks = [
        block
        for block in column_blocks
        if (
            float(block["x0"])
            + float(block["x1"])
        ) / 2.0 >= middle_x
    ]

    # 左右两栏都存在多个文本块，且垂直区域明显重叠时，
    # 才认为这是双栏页面，避免误伤普通单栏页面。
    is_two_column = False

    if (
        len(left_blocks) >= 2
        and len(right_blocks) >= 2
    ):
        left_top = min(
            float(block["y0"])
            for block in left_blocks
        )
        left_bottom = max(
            float(block["y1"])
            for block in left_blocks
        )

        right_top = min(
            float(block["y0"])
            for block in right_blocks
        )
        right_bottom = max(
            float(block["y1"])
            for block in right_blocks
        )

        vertical_overlap = (
            min(left_bottom, right_bottom)
            - max(left_top, right_top)
        )

        is_two_column = (
            vertical_overlap
            >= page_height * 0.18
        )

    def position_key(
        block: dict[str, object],
    ) -> tuple[float, float]:
        return (
            float(block["y0"]),
            float(block["x0"]),
        )

    if is_two_column:
        # 页面顶部的标题等跨栏内容先读取。
        top_full_width = [
            block
            for block in full_width_blocks
            if float(block["y0"])
            < page_height * 0.28
        ]

        remaining_full_width = [
            block
            for block in full_width_blocks
            if block not in top_full_width
        ]

        ordered_blocks = (
            sorted(
                top_full_width,
                key=position_key,
            )
            + sorted(
                left_blocks,
                key=position_key,
            )
            + sorted(
                right_blocks,
                key=position_key,
            )
            + sorted(
                remaining_full_width,
                key=position_key,
            )
        )

    else:
        # 普通单栏页面仍按从上到下、从左到右排列。
        ordered_blocks = sorted(
            normal_blocks,
            key=position_key,
        )

    body_text = "\n".join(
        str(block["text"])
        for block in ordered_blocks
        if str(block["text"]).strip()
    ).strip()

    footnote_text = "\n".join(
        str(block["text"])
        for block in sorted(
            footnotes,
            key=position_key,
        )
        if str(block["text"]).strip()
    ).strip()

    return body_text, footnote_text


def _normalize_margin_line(text: str) -> str:
    """规范化页眉页脚文本，便于跨页统计重复内容。"""

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip().casefold()


def _remove_repeated_page_margins(
    page_texts: list[str],
    *,
    remove_page_numbers: bool = True,
) -> list[str]:
    """
    自动清理跨页面重复出现的页眉、页脚和页码。

    只检查每页开头和结尾的少量行，
    避免误删正文中正常重复出现的内容。
    """

    if len(page_texts) < 3:
        return page_texts

    edge_line_count = 6

    page_lines: list[list[str]] = []
    top_counter: Counter[str] = Counter()
    bottom_counter: Counter[str] = Counter()

    for page_text in page_texts:
        lines = [
            line.strip()
            for line in page_text.splitlines()
            if line.strip()
        ]

        page_lines.append(lines)

        for line in lines[:edge_line_count]:
            normalized = _normalize_margin_line(
                line
            )

            if len(normalized) >= 4:
                top_counter[normalized] += 1

        for line in lines[-edge_line_count:]:
            normalized = _normalize_margin_line(
                line
            )

            if len(normalized) >= 4:
                bottom_counter[normalized] += 1

    # 至少出现在 60% 页面中，才视为重复页眉/页脚。
    repeat_threshold = max(
        3,
        (len(page_texts) * 6 + 9) // 10,
    )

    repeated_margin_lines = {
        text
        for text, count in (
            top_counter + bottom_counter
        ).items()
        if count >= repeat_threshold
    }

    cleaned_pages: list[str] = []

    for lines in page_lines:
        cleaned_lines: list[str] = []
        line_count = len(lines)

        for index, line in enumerate(lines):
            normalized = _normalize_margin_line(
                line
            )

            is_margin_area = (
                index < edge_line_count
                or index >= (
                    line_count
                    - edge_line_count
                )
            )

            # 删除重复页眉/页脚。
            if (
                is_margin_area
                and normalized
                in repeated_margin_lines
            ):
                continue

            # 删除边缘位置的独立页码，例如 11、12、13。
            if (
                remove_page_numbers
                and is_margin_area
                and re.fullmatch(
                    r"(?:page\s*)?\d{1,4}",
                    normalized,
                )
            ):
                continue

            cleaned_lines.append(line)

        cleaned_text = "\n".join(
            cleaned_lines
        ).strip()

        if cleaned_text:
            cleaned_pages.append(
                cleaned_text
            )

    return cleaned_pages


def extract_pdf_text(
    pdf_content: bytes,
) -> PdfExtractionResult:
    """
    从 PDF 原始字节中提取全文。

    当前仅处理包含可直接提取文本层的 PDF。
    扫描型 PDF 的 OCR 后续单独处理。
    """

    if not pdf_content:
        raise ValueError("PDF 内容为空。")

    try:
        document = fitz.open(
            stream=pdf_content,
            filetype="pdf",
        )

    except Exception as exc:
        raise ValueError(
            f"无法打开 PDF：{exc}"
        ) from exc

    try:
        page_count = document.page_count

        if page_count <= 0:
            raise ValueError(
                "PDF 不包含有效页面。"
            )

        page_texts: list[str] = []
        non_empty_page_count = 0
        page_footnotes: list[str] = []

        for page_number in range(page_count):
            page = document.load_page(
                page_number
            )

            text, footnote_text = (
                _extract_page_text_in_reading_order(
                    page
                )
            )

            if text:
                text = fix_text(text).strip()
            else:
                text = ""

            if footnote_text:
                footnote_text = fix_text(
                    footnote_text
                ).strip()
            else:
                footnote_text = ""

            if text:
                non_empty_page_count += 1
                page_texts.append(text)

            if footnote_text:
                page_footnotes.append(
                    f"第 {page_number + 1} 页注释：\n"
                    f"{footnote_text}"
                )

        cleaned_page_texts = (
            _remove_repeated_page_margins(
                page_texts
            )
        )

        body_text = "\n\n".join(
            cleaned_page_texts
        ).strip()

        cleaned_page_footnotes = (
            _remove_repeated_page_margins(
                page_footnotes,
                remove_page_numbers=False,
            )
        )

        page_footnotes_without_page_numbers: list[str] = []

        for note_text in cleaned_page_footnotes:
            note_lines = [
                line.rstrip()
                for line in note_text.splitlines()
            ]

            while (
                note_lines
                and not note_lines[-1].strip()
            ):
                note_lines.pop()

            # 此时 ATLANTIC COUNCIL 等重复页眉已经清除，
            # 因此最后一行纯数字才可以安全视为 PDF 页码。
            if (
                note_lines
                and re.fullmatch(
                    r"\d{1,4}",
                    note_lines[-1].strip(),
                )
            ):
                note_lines.pop()

            cleaned_note_text = "\n".join(
                note_lines
            ).strip()

            if cleaned_note_text:
                page_footnotes_without_page_numbers.append(
                    cleaned_note_text
                )

        cleaned_page_footnotes = (
            page_footnotes_without_page_numbers
        )

        # 清理后如果只剩“第 N 页注释：”标题，
        # 说明这一页原先只是页码/重复页眉被误识别为脚注，
        # 直接丢弃这个空脚注项。
        cleaned_page_footnotes = [
            text
            for text in cleaned_page_footnotes
            if not re.fullmatch(
                r"第\s*\d+\s*页注释：?\s*(?:\d{1,4}\s*)?",
                text.strip(),
            )
        ]

        footnotes_text = "\n\n".join(
            cleaned_page_footnotes
        ).strip()

        if footnotes_text:
            full_text = (
                f"{body_text}\n\n"
                "【注释与参考文献】\n\n"
                f"{footnotes_text}"
            ).strip()
        else:
            full_text = body_text

        return PdfExtractionResult(
            text=full_text,
            page_count=page_count,
            non_empty_page_count=(
                non_empty_page_count
            ),
        )

    finally:
        document.close()
