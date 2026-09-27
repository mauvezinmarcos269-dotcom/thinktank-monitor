import pytest

from app.scripts.pilot_crawl_sources import ensure_pilot_allowed, parse_keys


def test_parse_keys_normalizes_comma_separated_values() -> None:
    assert parse_keys(" CFR, piie ,, ") == [
        "cfr",
        "piie",
    ]


def test_ensure_pilot_allowed_accepts_current_pilot_sources() -> None:
    ensure_pilot_allowed(
        [
            "aei",
            "brookings",
            "cfr",
            "csis",
            "piie",
        ]
    )


def test_ensure_pilot_allowed_rejects_sources_still_under_review() -> None:
    with pytest.raises(ValueError, match="new_source"):
        ensure_pilot_allowed(
            [
                "cfr",
                "new_source",
            ]
        )


def test_ensure_pilot_allowed_accepts_standard_review_with_explicit_flag() -> None:
    ensure_pilot_allowed(
        [
            "new_source",
        ],
        allow_standard_review=True,
    )


@pytest.mark.parametrize("key", ["cato", "heritage"])
def test_ensure_pilot_allowed_rejects_blocked_sources(key: str) -> None:
    with pytest.raises(ValueError, match=key):
        ensure_pilot_allowed(
            [
                key,
            ],
            allow_standard_review=True,
        )
