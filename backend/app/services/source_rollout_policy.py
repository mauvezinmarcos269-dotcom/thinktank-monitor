from __future__ import annotations

from dataclasses import dataclass

ROLLOUT_STAGE_PILOT_CRAWL = "pilot_crawl"
ROLLOUT_STAGE_DISCOVERY_ONLY = "discovery_only"
ROLLOUT_STAGE_BLOCKED = "blocked"
ROLLOUT_STAGE_STANDARD_REVIEW = "standard_review"

DOCUMENT_POLICY_PDF_20_PAGE_REQUIRED = "pdf_20_page_required"
DOCUMENT_POLICY_WEB_ARTICLE_ALLOWED = "web_article_allowed"
DOCUMENT_POLICY_SOURCE_ACCESS_BLOCKED = "source_access_blocked"


@dataclass(frozen=True)
class SourceRolloutPolicy:
    key: str
    rollout_stage: str
    document_policy: str
    can_run_pilot_crawl: bool
    advice: str


PILOT_CRAWL_KEYS = {
    "aei",
    "brookings",
    "cfr",
    "csis",
    "ecfr",
    "piie",
}

DISCOVERY_ONLY_KEYS: set[str] = set()

BLOCKED_KEYS = {
    "cap",
    "cato",
    "heritage",
}

WEB_ARTICLE_ALLOWED_KEYS = {
    "aei",
    "ecfr",
}


def get_source_rollout_policy(key: str) -> SourceRolloutPolicy:
    normalized_key = key.strip().lower()

    if normalized_key in PILOT_CRAWL_KEYS:
        document_policy = DOCUMENT_POLICY_PDF_20_PAGE_REQUIRED
        advice = (
            "已通过真实小样本文档复核，可作为第一批入库抓取试点；"
            "仍需保留 20 页 PDF 门槛并观察跳过原因。"
        )

        if normalized_key in WEB_ARTICLE_ALLOWED_KEYS:
            document_policy = DOCUMENT_POLICY_WEB_ARTICLE_ALLOWED
            advice = (
                "已通过扩大样本只读复核，可进入小批量入库试运行；"
                "允许足够长、报告型网页正文作为正式报告入库，"
                "但仍需限制保存数量并人工复核样本质量。"
            )

        return SourceRolloutPolicy(
            key=normalized_key,
            rollout_stage=ROLLOUT_STAGE_PILOT_CRAWL,
            document_policy=document_policy,
            can_run_pilot_crawl=True,
            advice=advice,
        )

    if normalized_key in DISCOVERY_ONLY_KEYS:
        document_policy = DOCUMENT_POLICY_PDF_20_PAGE_REQUIRED
        advice = (
            "先保留候选发现，不建议直接进入批量入库抓取；"
            "小样本显示 PDF 缺失或页数不足导致跳过率较高。"
        )

        if normalized_key in WEB_ARTICLE_ALLOWED_KEYS:
            document_policy = DOCUMENT_POLICY_WEB_ARTICLE_ALLOWED
            advice = (
                advice
                + " 已确认允许足够长、报告型网页正文作为正式报告入库。"
            )

        return SourceRolloutPolicy(
            key=normalized_key,
            rollout_stage=ROLLOUT_STAGE_DISCOVERY_ONLY,
            document_policy=document_policy,
            can_run_pilot_crawl=False,
            advice=advice,
        )

    if normalized_key in BLOCKED_KEYS:
        return SourceRolloutPolicy(
            key=normalized_key,
            rollout_stage=ROLLOUT_STAGE_BLOCKED,
            document_policy=DOCUMENT_POLICY_SOURCE_ACCESS_BLOCKED,
            can_run_pilot_crawl=False,
            advice=(
                "当前普通 HTTP 抓取被站点防护拦截或无法稳定取得正文，"
                "需先确认官方 feed、可授权 API 或人工维护入口。"
            ),
        )

    return SourceRolloutPolicy(
        key=normalized_key,
        rollout_stage=ROLLOUT_STAGE_STANDARD_REVIEW,
        document_policy=DOCUMENT_POLICY_PDF_20_PAGE_REQUIRED,
        can_run_pilot_crawl=False,
        advice="尚未完成真实小样本文档复核，进入入库抓取前应先跑只读闭环检查。",
    )
