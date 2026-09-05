"""Official Albion refining recipes (gameinfo omits craftResourceList for refined resources).

Ratios match Sandbox refining guide:
  T2: 1 raw
  T3–T4: 2 raw + 1 previous refined
  T5: 3 raw + 1 previous
  T6: 4 raw + 1 previous
  T7–T8: 5 raw + 1 previous

Enchanted refined resources use *_LEVEL{n} unique names (same as gear recipes).
Focus base costs from community refining tables (pre-spec); used for silver/focus ranking.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

REFINE_FAMILIES: Dict[str, Dict[str, str]] = {
    "METALBAR": {"raw": "ORE", "label_en": "Metal bars", "label_pt": "Barras de metal"},
    "LEATHER": {"raw": "HIDE", "label_en": "Leather", "label_pt": "Couro"},
    "CLOTH": {"raw": "FIBER", "label_en": "Cloth", "label_pt": "Tecido"},
    "PLANKS": {"raw": "WOOD", "label_en": "Planks", "label_pt": "Tábuas"},
    "STONEBLOCK": {"raw": "ROCK", "label_en": "Stone blocks", "label_pt": "Blocos de pedra"},
}

# Raw materials needed per refined unit (official guide)
RAW_COUNT_BY_TIER: Dict[int, int] = {
    2: 1,
    3: 2,
    4: 2,
    5: 3,
    6: 4,
    7: 5,
    8: 5,
}

# Focus base cost by tier and enchant (0=flat, 1–3 = LEVEL1–3)
FOCUS_BASE: Dict[int, Dict[int, int]] = {
    2: {0: 18, 1: 33, 2: 54, 3: 90},
    3: {0: 31, 1: 55, 2: 91, 3: 151},
    4: {0: 48, 1: 89, 2: 143, 3: 239},
    5: {0: 89, 1: 160, 2: 269, 3: 461},
    6: {0: 160, 1: 284, 2: 487, 3: 844},
    7: {0: 284, 1: 500, 2: 866, 3: 1508},
    8: {0: 500, 1: 877, 2: 1527, 3: 2666},
}

# Cities with strongest refining specialty (informational defaults for UI)
CITY_BONUS_HINT: Dict[str, str] = {
    "METALBAR": "Thetford",
    "LEATHER": "Martlock",
    "CLOTH": "Lymhurst",
    "PLANKS": "Fort Sterling",
    "STONEBLOCK": "Bridgewatch",
}


def parse_refined_unique(unique_name: str) -> Optional[Tuple[int, str, int]]:
    """
    Parse T5_METALBAR / T5_METALBAR_LEVEL2 / T5_METALBAR@2
    -> (tier, family, enchant)
    """
    raw = (unique_name or "").strip().upper()
    if not raw:
        return None
    enchant = 0
    base = raw
    if "@" in raw:
        base, enc_s = raw.split("@", 1)
        try:
            enchant = int(enc_s)
        except ValueError:
            return None
    elif "_LEVEL" in raw:
        # T5_METALBAR_LEVEL2
        parts = raw.rsplit("_LEVEL", 1)
        if len(parts) != 2:
            return None
        base, enc_s = parts
        try:
            enchant = int(enc_s)
        except ValueError:
            return None

    # base like T5_METALBAR
    if not base.startswith("T") or "_" not in base:
        return None
    try:
        tier = int(base[1:].split("_", 1)[0])
    except ValueError:
        return None
    family = base.split("_", 1)[1]
    if family not in REFINE_FAMILIES:
        return None
    if tier < 2 or tier > 8:
        return None
    if enchant < 0 or enchant > 4:
        return None
    return tier, family, enchant


def refined_unique(tier: int, family: str, enchant: int = 0) -> str:
    base = f"T{tier}_{family}"
    if enchant <= 0:
        return base
    return f"{base}_LEVEL{enchant}"


def raw_unique(tier: int, family: str, enchant: int = 0) -> str:
    raw_family = REFINE_FAMILIES[family]["raw"]
    base = f"T{tier}_{raw_family}"
    if enchant <= 0:
        return base
    return f"{base}_LEVEL{enchant}"


def build_refine_recipe(unique_name: str) -> Optional[dict]:
    """Normalized recipe matching craft recipe_cache shape."""
    parsed = parse_refined_unique(unique_name)
    if not parsed:
        return None
    tier, family, enchant = parsed
    raw_count = RAW_COUNT_BY_TIER.get(tier)
    if raw_count is None:
        return None

    materials: List[dict] = []
    materials.append(
        {
            "unique_name": raw_unique(tier, family, enchant),
            "count": raw_count,
        }
    )
    if tier >= 3:
        materials.append(
            {
                "unique_name": refined_unique(tier - 1, family, enchant),
                "count": 1,
            }
        )

    focus_map = FOCUS_BASE.get(tier) or {}
    focus = focus_map.get(min(enchant, 3))

    product = refined_unique(tier, family, enchant)
    return {
        "unique_name": product,
        "enchant": enchant,
        "tier": tier,
        "family": family,
        "focus_cost": float(focus) if focus is not None else None,
        "silver": 0.0,
        "time": None,
        "materials": materials,
        "source": "official_refine_table",
        "bonus_city": CITY_BONUS_HINT.get(family),
    }


def list_common_refine_targets(
    *,
    families: Optional[List[str]] = None,
    tiers: Optional[List[int]] = None,
    enchants: Optional[List[int]] = None,
) -> List[str]:
    """T4–T8 common refine chains (flat by default)."""
    fams = families or ["METALBAR", "LEATHER", "CLOTH", "PLANKS"]
    trs = tiers or list(range(4, 9))
    encs = enchants if enchants is not None else [0]
    out: List[str] = []
    for family in fams:
        if family not in REFINE_FAMILIES:
            continue
        for tier in trs:
            if tier < 2 or tier > 8:
                continue
            for enc in encs:
                out.append(refined_unique(tier, family, enc))
    return out
