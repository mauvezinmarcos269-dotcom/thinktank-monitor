from __future__ import annotations

import json
import logging

from app.core.llm import SiliconFlowClient

logger = logging.getLogger(__name__)


RELEVANCE_SAMPLE_LENGTH = 12000


def _sample_report_content(
    content: str,
) -> str:
    """
    从长报告的开头、中部和结尾进行均匀取样，
    避免只检查报告前部造成相关性误判。
    """
    if len(content) <= RELEVANCE_SAMPLE_LENGTH:
        return content

    section_length = RELEVANCE_SAMPLE_LENGTH // 3

    start = content[:section_length]

    middle_start = max(
        0,
        len(content) // 2 - section_length // 2,
    )
    middle = content[
        middle_start:
        middle_start + section_length
    ]

    end = content[-section_length:]

    return (
        "===== 报告开头 =====\n"
        f"{start}\n\n"
        "===== 报告中部 =====\n"
        f"{middle}\n\n"
        "===== 报告结尾 =====\n"
        f"{end}"
    )


def _build_relevance_prompt(
    title: str,
    content: str,
) -> str:
    return f"""
你需要判断一篇智库研究材料是否属于本平台需要长期追踪的“涉华研究”。

判断标准：

1. direct
中国、中国政府、中国经济、中国外交、中国军事、中国科技、中国企业、
台湾、香港、南海、中美关系等是报告的主要研究对象。

2. substantial
报告主题不完全以中国为中心，但中国在核心论证、战略竞争、政策建议、
地区安全、产业链、科技、贸易或国际格局分析中占有重要篇幅，
不理解中国因素就无法理解报告主要结论。

3. incidental
只是零散提及中国，例如作为多个国家之一、背景信息、引用案例或一句比较。

4. unrelated
基本与中国无关。

只有 direct 或 substantial 才算涉华。
incidental 和 unrelated 均不算涉华。

必须严格依据给出的标题和正文判断，不得仅因为出现 China、Chinese、
Beijing、Taiwan 等关键词就判定为涉华。

你必须只输出合法 JSON，不要 Markdown，不要解释 JSON 之外的内容。

JSON 格式必须严格为：

{{
  "relevance": "direct|substantial|incidental|unrelated",
  "is_china_related": true,
  "reason": "用中文简要说明判断理由"
}}

标题：
{title}

正文：
{content}
""".strip()


def _parse_relevance_result(
    raw_result: str,
) -> dict[str, str | bool]:
    if not raw_result:
        raise ValueError("涉华判断返回为空")

    try:
        data = json.loads(raw_result)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "涉华判断返回的不是有效 JSON"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            "涉华判断结果不是 JSON 对象"
        )

    relevance = str(
        data.get("relevance", "")
    ).strip().lower()

    allowed = {
        "direct",
        "substantial",
        "incidental",
        "unrelated",
    }

    if relevance not in allowed:
        raise ValueError(
            f"无效的 relevance: {relevance}"
        )

    reason = str(
        data.get("reason", "")
    ).strip()

    return {
        "relevance": relevance,
        "is_china_related": relevance
        in {"direct", "substantial"},
        "reason": reason,
    }


async def evaluate_china_relevance(
    title: str,
    content: str,
) -> dict[str, str | bool]:
    """
    判断报告是否属于需要进一步处理的涉华研究。

    这里只承担准入判断，不生成翻译、摘要或评论。
    """
    if not content:
        raise ValueError(
            "报告正文不能为空"
        )

    sampled_content = _sample_report_content(
        content
    )

    prompt = _build_relevance_prompt(
        title or "未命名报告",
        sampled_content,
    )

    async with SiliconFlowClient() as client:
        raw_result = await client.chat(
            prompt=prompt,
            temperature=0.0,
            max_tokens=500,
        )

    result = _parse_relevance_result(
        raw_result
    )

    logger.info(
        "China relevance evaluated: "
        "title=%s, relevance=%s, "
        "is_china_related=%s",
        title,
        result["relevance"],
        result["is_china_related"],
    )

    return result
