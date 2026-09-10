from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
from ftfy import fix_text

PREFERRED_MIN_CONTENT_LENGTH = 300

FALLBACK_MIN_CONTENT_LENGTH = 150

def extract_report_pdf_url(
    html: str | bytes,
    base_url: str,
) -> str | None:
    """
    从报告详情页 HTML 中寻找最可能的报告 PDF 链接。

    优先级：
    1. 链接地址本身指向 PDF；
    2. 链接文字包含 download pdf；
    3. 链接文字包含 full report / full text。

    相对链接会根据 base_url 转换为绝对链接。
    """
    soup = BeautifulSoup(html, "html.parser")

    candidates: list[tuple[int, str]] = []

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "").strip()

        if not href:
            continue

        absolute_url = urljoin(base_url, href)

        parsed = urlsplit(absolute_url)

        if parsed.scheme not in {"http", "https"}:
            continue

        link_text = " ".join(anchor.stripped_strings).strip().lower()
        url_lower = absolute_url.lower()
        path_lower = parsed.path.lower()

        score = 0

        if path_lower.endswith(".pdf") or ".pdf" in path_lower:
            score += 10

        if "download pdf" in link_text:
            score += 8
        elif "pdf" in link_text:
            score += 4

        if "read the full report" in link_text:
            score += 6
        elif "full report" in link_text:
            score += 5
        elif "full text" in link_text:
            score += 3

        if ".pdf" in url_lower:
            score += 2

        has_pdf_target = ".pdf" in url_lower

        # 只有具备明确“报告下载”语义的 PDF 才作为候选。
        # 单纯正文中引用的外部 PDF 不能被当作本报告附件。
        has_report_intent = (
            "download pdf" in link_text
            or "download report" in link_text
            or "download" == link_text
            or "read the full report" in link_text
            or "full report" in link_text
            or "report pdf" in link_text
        )

        if score > 0 and has_pdf_target and has_report_intent:
            candidates.append(
                (
                    score,
                    absolute_url,
                )
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return candidates[0][1]


def _is_noise_line(line: str) -> bool:
    """
    对已经提取出来的纯文本做轻量级噪声过滤。

    注意：
    这里不再操作 BeautifulSoup DOM，只针对文本行进行判断，
    避免 element.decompose() 对正文节点树造成二次影响。
    """
    normalized = " ".join(line.split()).strip()

    if not normalized:
        return True

    lower = normalized.lower()

    exact_noise = {
        "share",
        "sharing",
        "share this",
        "share this article",
        "subscribe",
        "newsletter",
        "sign up",
        "sign up for our newsletter",
        "newsletter signup",
        "related articles",
        "related posts",
        "recommended articles",
        "read more",
        "more stories",
    }

    if lower in exact_noise:
        return True

    noise_patterns = (
        r"^share\s+(this\s+)?(article|story|report)?$",
        r"^subscribe\s+(to|for)\b",
        r"^sign\s*up\b.*newsletter",
        r"^get\s+our\s+newsletter\b",
        r"^related\s+(articles?|posts?|stories?)$",
        r"^recommended\s+(articles?|posts?|stories?)$",
        r"^read\s+more$",
    )

    for pattern in noise_patterns:
        if re.search(pattern, lower):
            return True

    return False


def _clean_extracted_text(text: str) -> str | None:
    """
    对已经从正文节点提取出的纯文本进行清洗。

    不重新操作 BeautifulSoup DOM。
    """
    if not text:
        return None

    text = fix_text(text)

    text = (
        text.replace("\u00a0", " ")
        .replace("\u200b", "")
        .replace("\u200c", "")
        .replace("\u200d", "")
        .replace("\ufeff", "")
    )

    lines: list[str] = []

    for line in text.splitlines():
        cleaned_line = " ".join(line.split())

        if not cleaned_line:
            continue

        if _is_noise_line(cleaned_line):
            continue

        lines.append(cleaned_line)

    content = "\n".join(lines).strip()

    return content or None


def extract_article_content(
    html: str | bytes,
) -> str | None:
    """
    从报告详情页 HTML 中提取并清洗正文纯文本。

    参数：
        html:
            网页 HTML，可以是 str，也可以是原始 bytes。
            推荐传入 HTTP 响应的原始 bytes。

    返回：
        清洗后的正文；
        无法提取时返回 None。
    """
    if isinstance(html, str):
        html = fix_text(html)

    soup = BeautifulSoup(html, "html.parser")

    # ============================================================
    # 第一轮：从整个页面中移除确定不是正文的节点
    # ============================================================
    noise_selectors = (
        "script, style, nav, header, footer, aside, form, noscript, "
        "iframe, svg, button, "
        ".related-content, .related-posts, .related-articles, "
        ".related, .recommendations, .recommended, "
        ".newsletter, .newsletter-signup, .subscribe, "
        ".subscription, .signup, "
        ".social-share, .social-sharing, .share, .sharing, "
        ".author-bio, .author-box, .author-card, "
        ".tags, .categories, .breadcrumbs, "
        ".advertisement, .advertising, .ad-container, "
        ".promo, .promotion, "
        ".read-more, .more-stories, "
        "[class*='related-post'], "
        "[class*='related-article'], "
        "[class*='newsletter'], "
        "[class*='social-share']"
    )

    for element in soup.select(noise_selectors):
        element.decompose()

    # ============================================================
    # 正文选择器
    # ============================================================
    selectors = [
        "article .article-content",
        "article .article-body",
        "article .entry-content",
        "article .post-content",
        "article .story-content",
        "article .body-content",
        "article [itemprop='articleBody']",
        "[itemprop='articleBody']",
        ".article-content",
        ".article-body",
        ".entry-content",
        ".post-content",
        ".story-content",
        "article",
        "main",
    ]

    # ============================================================
    # 第一阶段：
    # 优先寻找 >= 300 字的正文节点。
    # ============================================================
    fallback_text: str | None = None

    for selector in selectors:
        candidate = soup.select_one(selector)

        if candidate is None:
            continue

        candidate_text = candidate.get_text(
            "\n",
            strip=True,
        )

        if not candidate_text:
            continue

        # 先进行文本级清洗，再判断最终长度。
        cleaned_candidate = _clean_extracted_text(candidate_text)

        if not cleaned_candidate:
            continue

        # 保留一个 150~299 字的候选作为兜底。
        if (
            fallback_text is None
            and len(cleaned_candidate) >= FALLBACK_MIN_CONTENT_LENGTH
        ):
            fallback_text = cleaned_candidate

        # 优先使用 >=300 字的候选。
        if len(cleaned_candidate) >= PREFERRED_MIN_CONTENT_LENGTH:
            return cleaned_candidate

    # ============================================================
    # 第二阶段：
    # 没有找到 >=300 字正文时，接受 >=150 字的候选。
    # ============================================================
    if fallback_text is not None:
        return fallback_text

    return None

