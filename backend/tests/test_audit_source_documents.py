from app.scripts.audit_source_documents import (
    audit_source_documents,
    build_sources,
    deduplicate_articles,
)
from app.services.source_rollout_policy import ROLLOUT_STAGE_PILOT_CRAWL


class _FakeSource:
    source_type = "website"
    url = "https://www.aei.org/"


def test_build_sources_uses_requested_seed_keys() -> None:
    sources = build_sources(
        [
            "aei",
            "heritage",
        ]
    )

    assert [key for key, _name, _source in sources] == [
        "heritage",
        "aei",
    ]
    assert [source.url for _key, _name, source in sources] == [
        "https://www.heritage.org/",
        "https://www.aei.org/",
    ]


def test_deduplicate_articles_keeps_first_normalized_url() -> None:
    articles = [
        {
            "title": "First",
            "url": "https://example.org/reports/china/",
        },
        {
            "title": "Duplicate",
            "url": "https://example.org/reports/china#section",
        },
        {
            "title": "Second",
            "url": "https://example.org/reports/taiwan",
        },
    ]

    unique_articles, duplicate_count = deduplicate_articles(
        articles
    )

    assert duplicate_count == 1
    assert [article["title"] for article in unique_articles] == [
        "First",
        "Second",
    ]


async def test_audit_source_documents_includes_rollout_policy(
    monkeypatch,
) -> None:
    async def fake_fetch_source_articles(_source):
        return []

    monkeypatch.setattr(
        "app.scripts.audit_source_documents.fetch_source_articles",
        fake_fetch_source_articles,
    )

    result = await audit_source_documents(
        key="aei",
        name="American Enterprise Institute",
        source=_FakeSource(),  # type: ignore[arg-type]
        discovery_timeout_seconds=1,
        document_timeout_seconds=1,
        max_candidates=1,
    )

    assert result["status"] == "ok"
    assert result["rollout_stage"] == ROLLOUT_STAGE_PILOT_CRAWL
    assert result["can_run_pilot_crawl"] is True
