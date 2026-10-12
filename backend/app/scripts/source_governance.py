from typing import Any

from app.models.think_tank import PriorityTierEnum, RegionFocusEnum

P0_KEYS = {
    "brookings",
    "csis",
    "rand",
    "cfr",
    "carnegie",
    "piie",
}

P1_KEYS = {
    "heritage",
    "aei",
    "hoover",
    "wilson",
    "cato",
    "cap",
    "nber",
    "atlantic_council",
}

P2_KEYS = {
    "chatham_house",
    "bruegel",
    "ifri",
    "swp",
    "dgap",
    "ecfr",
    "iiss",
    "sipri",
}

P3_KEYS = {
    "jiia",
    "rieti",
    "eria",
    "kdi",
    "kiep",
}

DOMESTIC_REFERENCE_KEYS = {
    "siis",
    "cicir",
}


def derive_source_governance(
    item: dict[str, Any],
) -> tuple[PriorityTierEnum, RegionFocusEnum, bool]:
    key = str(item["key"])

    if key in P0_KEYS:
        return (
            PriorityTierEnum.p0,
            RegionFocusEnum.us,
            True,
        )

    if key in P1_KEYS:
        return (
            PriorityTierEnum.p1,
            RegionFocusEnum.us,
            True,
        )

    if key in P2_KEYS:
        return (
            PriorityTierEnum.p2,
            RegionFocusEnum.europe,
            True,
        )

    if key in P3_KEYS:
        return (
            PriorityTierEnum.p3,
            RegionFocusEnum.neighboring,
            True,
        )

    if key in DOMESTIC_REFERENCE_KEYS:
        return (
            PriorityTierEnum.p4,
            RegionFocusEnum.domestic,
            True,
        )

    return (
        PriorityTierEnum.p4,
        RegionFocusEnum.candidate,
        False,
    )
