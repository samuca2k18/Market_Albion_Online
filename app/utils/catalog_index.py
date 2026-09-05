"""Local Albion catalog built from nomes_*.json / albion_index (no OpenAlbion)."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Literal, Optional

from app.utils.albion_index import ALBION_ITEMS, ITEM_BY_UNIQUE, normalizar

ItemType = Literal["weapon", "armor", "accessory", "consumable"]
Lang = Literal["pt_br", "en_us"]

RENDER_ICON = "https://render.albiononline.com/v1/item/{unique}.png"

_TIER_RE = re.compile(r"^T(\d+)_", re.IGNORECASE)
_ENCHANT_RE = re.compile(r"@(\d+)$")

# Weapon family token → display name
_WEAPON_FAMILY_NAMES: Dict[str, str] = {
    "SWORD": "Swords",
    "CLAYMORE": "Claymores",
    "DUALSWORD": "Dual Swords",
    "AXE": "Axes",
    "HALBERD": "Halberds",
    "SCYTHE": "Scythes",
    "CARVING": "Carving Axes",
    "MACE": "Maces",
    "HEAVYMACE": "Heavy Maces",
    "MORNINGSTAR": "Morning Stars",
    "HAMMER": "Hammers",
    "GREATHAMMER": "Great Hammers",
    "POLEHAMMER": "Polehammers",
    "DUALHAMMER": "Dual Hammers",
    "SPEAR": "Spears",
    "PIKE": "Pikes",
    "GLAIVE": "Glaives",
    "TRIDENT": "Tridents",
    "DAGGER": "Daggers",
    "DAGGERPAIR": "Dagger Pairs",
    "CLAWPAIR": "Claws",
    "BOW": "Bows",
    "LONGBOW": "Longbows",
    "WARBOW": "Warbows",
    "CROSSBOW": "Crossbows",
    "CROSSBOWLARGE": "Heavy Crossbows",
    "DUALCROSSBOW": "Dual Crossbows",
    "FIRESTAFF": "Fire Staffs",
    "INFERNOSTAFF": "Infernal Staffs",
    "WILDFIRESTAFF": "Wildfire Staffs",
    "FROSTSTAFF": "Frost Staffs",
    "GLACIALSTAFF": "Glacial Staffs",
    "ICICLESTAFF": "Icicle Staffs",
    "HOLYSTAFF": "Holy Staffs",
    "DIVINESTAFF": "Divine Staffs",
    "LIFETOUCHSTAFF": "Lifetouch Staffs",
    "NATURESTAFF": "Nature Staffs",
    "WILDSTAFF": "Wild Staffs",
    "ARCANESTAFF": "Arcane Staffs",
    "ENIGMATICSTAFF": "Enigmatic Staffs",
    "CURSEDSTAFF": "Cursed Staffs",
    "DEMONICSTAFF": "Demonic Staffs",
    "QUARTERSTAFF": "Quarterstaffs",
    "IRONCLADEDSTAFF": "Iron-clad Staffs",
    "DOUBLEBLADEDSTAFF": "Double-bladed Staffs",
    "BLACKMONKSTAFF": "Black Monk Staffs",
    "SHIELD": "Shields",
    "TOWERSHIELD": "Tower Shields",
    "SPIKEDSHIELD": "Spiked Shields",
    "TORCH": "Torches",
    "BOOK": "Tomes",
    "TOME": "Tomes",
    "ORB": "Orbs",
    "HORN": "Horns",
    "TOTEM": "Totems",
    "CENSER": "Censers",
    "DEMONSKULL": "Demon Skulls",
    "KNUCKLES": "Knuckles",
    "SHAPESHIFTER": "Shapeshifter Staffs",
    "TOOL": "Tools",
}

_ARMOR_SLOT_NAMES = {"HEAD": "Head", "ARMOR": "Armor", "SHOES": "Shoes"}
_ARMOR_MAT_NAMES = {
    "CLOTH": "Cloth",
    "LEATHER": "Leather",
    "PLATE": "Plate",
    "GATHERER": "Gatherer",
}


def stable_id(key: str) -> int:
    """Stable positive 31-bit int from a string key."""
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) & 0x7FFFFFFF


def parse_tier(unique: str) -> Optional[str]:
    m = _TIER_RE.match(unique)
    return m.group(1) if m else None


def strip_tier_enchant(unique: str) -> str:
    base = _TIER_RE.sub("", unique)
    return _ENCHANT_RE.sub("", base)


def classify_unique(unique: str) -> Optional[ItemType]:
    """Heuristic item type from UniqueName. Returns None for untyped/other."""
    u = unique.upper()

    # Skip skins / furniture / journals — not useful in equipment tabs
    if u.startswith("SKIN_") or "FURNITURE" in u or "_JOURNAL_" in u:
        return None

    # Consumables (token-aware FOOD to avoid furniture/false positives)
    if "POTION" in u or "_MEAL_" in u or u.startswith("MEAL_"):
        return "consumable"
    if re.search(r"(^|_)FOOD(_|$)", u) and "FURNITURE" not in u:
        return "consumable"

    # Armor slots (path tokens) — before weapon so ARTEFACT_HEAD_* etc. land here
    if re.search(r"(^|_)(HEAD|ARMOR|SHOES)_", u):
        return "armor"

    # Weapons
    if re.search(r"(^|_)(2H|MAIN|OFF)_", u):
        return "weapon"

    # Accessories — token-aware to avoid CABBAGE / MOUNTAIN false positives
    if re.search(r"(^|_)BAG(?:_|@|$)", u) or re.search(r"^T\d+_BAG(?:@\d+)?$", u):
        return "accessory"
    if "CAPE" in u:
        return "accessory"
    if re.search(r"(^|_)MOUNT_", u) and "MOUNTUPGRADE" not in u:
        return "accessory"

    return None


def _weapon_family(unique: str) -> tuple[str, str]:
    """Return (category_key, display_name) for a weapon UniqueName."""
    u = unique.upper()
    if "ARTEFACT" in u:
        return ("ARTEFACT", "Artefacts")

    base = strip_tier_enchant(u)
    m = re.search(r"(?:MAIN|2H|OFF)_(.+)$", base)
    if not m:
        return ("OTHER", "Other")

    rest = m.group(1)
    # First token is the core family (SWORD, BOW, FIRESTAFF, …)
    family = rest.split("_")[0]
    if family == "BOOK":
        family = "TOME"
    name = _WEAPON_FAMILY_NAMES.get(family, family.replace("_", " ").title() + "s")
    return (family, name)


def _armor_category(unique: str) -> tuple[str, str]:
    u = unique.upper()
    if "ARTEFACT" in u:
        return ("ARTEFACT", "Artefacts")

    slot = None
    for s in ("HEAD", "ARMOR", "SHOES"):
        if re.search(rf"(^|_){s}_", u):
            slot = s
            break

    mat = None
    for m in ("CLOTH", "LEATHER", "PLATE", "GATHERER"):
        if f"_{m}_" in u or u.endswith(f"_{m}"):
            mat = m
            break

    if slot and mat:
        key = f"{slot}_{mat}"
        name = f"{_ARMOR_SLOT_NAMES[slot]} {_ARMOR_MAT_NAMES[mat]}"
        return (key, name)
    if slot:
        return (slot, _ARMOR_SLOT_NAMES[slot])
    return ("OTHER", "Other")


def _accessory_category(unique: str) -> tuple[str, str]:
    u = unique.upper()
    if re.search(r"(^|_)BAG(?:_|@|$)", u) or re.search(r"^T\d+_BAG(?:@\d+)?$", u):
        return ("BAG", "Bag")
    if "CAPE" in u:
        return ("CAPE", "Cape")
    if re.search(r"(^|_)MOUNT_", u):
        return ("MOUNT", "Mount")
    return ("OTHER", "Other")


def _consumable_category(unique: str) -> tuple[str, str]:
    u = unique.upper()
    if "POTION" in u:
        return ("POTION", "Potion")
    if "_MEAL_" in u or u.startswith("MEAL_"):
        return ("MEAL", "Meal")
    if re.search(r"(^|_)FOOD(_|$)", u):
        return ("FOOD", "Food")
    return ("OTHER", "Other")


def category_for(unique: str, item_type: ItemType) -> tuple[str, str]:
    if item_type == "weapon":
        return _weapon_family(unique)
    if item_type == "armor":
        return _armor_category(unique)
    if item_type == "accessory":
        return _accessory_category(unique)
    return _consumable_category(unique)


def category_id_for(item_type: ItemType, category_key: str) -> int:
    return stable_id(f"cat:{item_type}:{category_key}")


def item_id_for(unique: str) -> int:
    return stable_id(unique)


def icon_url(unique: str) -> str:
    return RENDER_ICON.format(unique=unique)


def localize_name(registro: dict, lang: Lang) -> str:
    if lang == "en_us":
        return registro.get("EN-US") or registro.get("PT-BR") or registro.get("UniqueName", "")
    return registro.get("PT-BR") or registro.get("EN-US") or registro.get("UniqueName", "")


def to_api_item(registro: dict, lang: Lang = "pt_br") -> dict[str, Any]:
    unique = registro["UniqueName"]
    tier = parse_tier(unique) or "0"
    return {
        "id": item_id_for(unique),
        "name": localize_name(registro, lang),
        "tier": tier,
        "item_power": 0,
        "icon": icon_url(unique),
        "unique_name": unique,
        "identifier": unique,
    }


# ── Precomputed typed indexes (built once at import) ───────────────────────

_TYPED: Dict[ItemType, List[dict]] = {
    "weapon": [],
    "armor": [],
    "accessory": [],
    "consumable": [],
}

# unique -> meta
_META: Dict[str, dict] = {}
# id -> unique
_ID_TO_UNIQUE: Dict[int, str] = {}
# (type, category_id) -> category_key
_CATEGORIES: Dict[ItemType, Dict[int, dict]] = {
    "weapon": {},
    "armor": {},
    "accessory": {},
    "consumable": {},
}


def _build_indexes() -> None:
    for registro in ALBION_ITEMS:
        unique = registro.get("UniqueName")
        if not unique:
            continue
        item_type = classify_unique(unique)
        if item_type is None:
            continue

        cat_key, cat_name = category_for(unique, item_type)
        cat_id = category_id_for(item_type, cat_key)
        iid = item_id_for(unique)
        tier = parse_tier(unique)

        meta = {
            "unique": unique,
            "type": item_type,
            "tier": tier,
            "category_id": cat_id,
            "category_key": cat_key,
            "registro": registro,
        }
        _META[unique] = meta
        _ID_TO_UNIQUE[iid] = unique
        _TYPED[item_type].append(meta)

        if cat_id not in _CATEGORIES[item_type]:
            _CATEGORIES[item_type][cat_id] = {
                "id": cat_id,
                "name": cat_name,
                "type": item_type,
                "subcategories": [],
                "_key": cat_key,
            }

    for t in _TYPED:
        _TYPED[t].sort(key=lambda m: (m["tier"] or "0", m["unique"]))


_build_indexes()


def list_categories(item_type: ItemType) -> List[dict]:
    cats = list(_CATEGORIES[item_type].values())
    cats.sort(key=lambda c: c["name"])
    return [
        {"id": c["id"], "name": c["name"], "type": c["type"], "subcategories": c["subcategories"]}
        for c in cats
    ]


def list_items(
    item_type: ItemType,
    *,
    tier: Optional[int] = None,
    category_id: Optional[int] = None,
    q: Optional[str] = None,
    lang: Lang = "pt_br",
    limit: int = 200,
    offset: int = 0,
) -> List[dict]:
    lang = "pt_br" if lang not in ("pt_br", "en_us") else lang
    limit = max(1, min(limit, 1000))
    offset = max(0, offset)

    q_norm = normalizar(q) if q else ""
    results: List[dict] = []

    for meta in _TYPED[item_type]:
        if tier is not None and meta["tier"] != str(tier):
            continue
        if category_id is not None and meta["category_id"] != category_id:
            continue
        if q_norm:
            reg = meta["registro"]
            name_pt = normalizar(reg.get("PT-BR", ""))
            name_en = normalizar(reg.get("EN-US", ""))
            uniq = meta["unique"].lower()
            if q_norm not in name_pt and q_norm not in name_en and q_norm not in uniq:
                continue
        results.append(to_api_item(meta["registro"], lang))

    return results[offset : offset + limit]


def get_item_by_id(item_id: int, lang: Lang = "pt_br") -> Optional[dict]:
    unique = _ID_TO_UNIQUE.get(item_id)
    if not unique:
        return None
    reg = ITEM_BY_UNIQUE.get(unique) or _META[unique]["registro"]
    return to_api_item(reg, lang)


def get_meta_by_id(item_id: int) -> Optional[dict]:
    unique = _ID_TO_UNIQUE.get(item_id)
    if not unique:
        return None
    return _META.get(unique)


def catalog_stats() -> dict:
    return {t: len(items) for t, items in _TYPED.items()}
