import pytest

from app.services.source_rollout_policy import (
    DOCUMENT_POLICY_PDF_20_PAGE_REQUIRED,
    DOCUMENT_POLICY_SOURCE_ACCESS_BLOCKED,
    DOCUMENT_POLICY_WEB_ARTICLE_ALLOWED,
    ROLLOUT_STAGE_BLOCKED,
    ROLLOUT_STAGE_PILOT_CRAWL,
    ROLLOUT_STAGE_STANDARD_REVIEW,
    get_source_rollout_policy,
)


@pytest.mark.parametrize("key", ["brookings", "cfr", "csis", "piie"])
def test_pilot_crawl_policy_for_verified_sample_sources(key: str) -> None:
    policy = get_source_rollout_policy(key)

    assert policy.rollout_stage == ROLLOUT_STAGE_PILOT_CRAWL
    assert policy.document_policy == DOCUMENT_POLICY_PDF_20_PAGE_REQUIRED
    assert policy.can_run_pilot_crawl is True


def test_aei_enters_pilot_crawl_with_web_article_allowed() -> None:
    policy = get_source_rollout_policy("aei")

    assert policy.rollout_stage == ROLLOUT_STAGE_PILOT_CRAWL
    assert policy.document_policy == DOCUMENT_POLICY_WEB_ARTICLE_ALLOWED
    assert policy.can_run_pilot_crawl is True


def test_ecfr_enters_pilot_crawl_with_web_article_allowed() -> None:
    policy = get_source_rollout_policy("ecfr")

    assert policy.rollout_stage == ROLLOUT_STAGE_PILOT_CRAWL
    assert policy.document_policy == DOCUMENT_POLICY_WEB_ARTICLE_ALLOWED
    assert policy.can_run_pilot_crawl is True


@pytest.mark.parametrize("key", ["cap", "cato", "heritage"])
def test_blocked_sources_wait_for_access_path(key: str) -> None:
    policy = get_source_rollout_policy(key)

    assert policy.rollout_stage == ROLLOUT_STAGE_BLOCKED
    assert policy.document_policy == DOCUMENT_POLICY_SOURCE_ACCESS_BLOCKED
    assert policy.can_run_pilot_crawl is False


def test_unknown_source_requires_standard_review() -> None:
    policy = get_source_rollout_policy("new_source")

    assert policy.rollout_stage == ROLLOUT_STAGE_STANDARD_REVIEW
    assert policy.document_policy == DOCUMENT_POLICY_PDF_20_PAGE_REQUIRED
    assert policy.can_run_pilot_crawl is False
