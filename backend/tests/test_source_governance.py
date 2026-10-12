from types import SimpleNamespace

import pytest

from app.models.source import Source, SourceTypeEnum
from app.models.think_tank import PriorityTierEnum, RegionFocusEnum
from app.scripts.seed_thinktank_data import SEED_THINK_TANKS
from app.scripts.seed_thinktanks import ensure_rss_source, ensure_website_source
from app.scripts.source_governance import derive_source_governance


class _FakeExecuteResult:
    def __init__(self, value: object | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object | None:
        return self.value


class _FakeDb:
    def __init__(self, existing: object | None = None) -> None:
        self.existing = existing
        self.added: list[object] = []

    async def execute(self, statement: object) -> _FakeExecuteResult:
        return _FakeExecuteResult(self.existing)

    def add(self, value: object) -> None:
        self.added.append(value)


@pytest.mark.parametrize(
    ("key", "expected_priority", "expected_region", "expected_verified"),
    [
        ("rand", PriorityTierEnum.p0, RegionFocusEnum.us, True),
        ("aei", PriorityTierEnum.p1, RegionFocusEnum.us, True),
        ("chatham_house", PriorityTierEnum.p2, RegionFocusEnum.europe, True),
        ("jiia", PriorityTierEnum.p3, RegionFocusEnum.neighboring, True),
        ("siis", PriorityTierEnum.p4, RegionFocusEnum.domestic, True),
        (
            "amnesty_international",
            PriorityTierEnum.p4,
            RegionFocusEnum.candidate,
            False,
        ),
    ],
)
def test_derives_expected_governance_for_representative_sources(
    key: str,
    expected_priority: PriorityTierEnum,
    expected_region: RegionFocusEnum,
    expected_verified: bool,
) -> None:
    item = next(seed_item for seed_item in SEED_THINK_TANKS if seed_item["key"] == key)

    priority_tier, region_focus, is_verified = derive_source_governance(item)

    assert priority_tier == expected_priority
    assert region_focus == expected_region
    assert is_verified is expected_verified


def test_derives_candidate_governance_for_unknown_source() -> None:
    priority_tier, region_focus, is_verified = derive_source_governance(
        {"key": "new_unreviewed_source"}
    )

    assert priority_tier == PriorityTierEnum.p4
    assert region_focus == RegionFocusEnum.candidate
    assert is_verified is False


def test_all_seed_sources_have_unique_keys_and_valid_governance() -> None:
    keys = [str(item["key"]) for item in SEED_THINK_TANKS]

    assert len(keys) == len(set(keys))

    for item in SEED_THINK_TANKS:
        priority_tier, region_focus, is_verified = derive_source_governance(item)

        assert isinstance(priority_tier, PriorityTierEnum)
        assert isinstance(region_focus, RegionFocusEnum)
        assert isinstance(is_verified, bool)


@pytest.mark.asyncio
async def test_website_source_uses_globally_unique_url() -> None:
    db = _FakeDb()

    await ensure_website_source(
        db,
        think_tank=SimpleNamespace(id=42),  # type: ignore[arg-type]
        website="https://example.org/",
    )

    assert len(db.added) == 1
    source = db.added[0]
    assert isinstance(source, Source)
    assert source.source_type == SourceTypeEnum.website
    assert source.url == "https://example.org/"


@pytest.mark.asyncio
async def test_existing_url_is_not_added_to_another_think_tank() -> None:
    existing = object()
    db = _FakeDb(existing=existing)

    await ensure_rss_source(
        db,
        think_tank=SimpleNamespace(id=99),  # type: ignore[arg-type]
        rss_url="https://example.org/feed.xml",
    )

    assert db.added == []
