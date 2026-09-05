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

# Family key → (en, pt_br)
_WEAPON_FAMILY_NAMES: Dict[str, tuple[str, str]] = {
    "SWORD": ("Swords", "Espadas"),
    "CLAYMORE": ("Claymores", "Claymores"),
    "DUALSWORD": ("Dual Swords", "Espadas Duplas"),
    "AXE": ("Axes", "Machados"),
    "HALBERD": ("Halberds", "Alabardas"),
    "SCYTHE": ("Scythes", "Foices"),
    "CARVING": ("Carving Axes", "Machados de Entalhe"),
    "CLEAVER": ("Cleavers", "Cutelos"),
    "DUALAXE": ("Dual Axes", "Machados Duplos"),
    "MACE": ("Maces", "Maças"),
    "HEAVYMACE": ("Heavy Maces", "Maças Pesadas"),
    "MORNINGSTAR": ("Morning Stars", "Estrelas da Manhã"),
    "DUALMACE": ("Dual Maces", "Maças Duplas"),
    "FLAIL": ("Flails", "Manguais"),
    "HAMMER": ("Hammers", "Martelos"),
    "GREATHAMMER": ("Great Hammers", "Grandes Martelos"),
    "POLEHAMMER": ("Polehammers", "Martelos de Haste"),
    "DUALHAMMER": ("Dual Hammers", "Martelos Duplos"),
    "SPEAR": ("Spears", "Lanças"),
    "PIKE": ("Pikes", "Piques"),
    "GLAIVE": ("Glaives", "Glaives"),
    "TRIDENT": ("Tridents", "Tridentes"),
    "HARPOON": ("Harpoons", "Arpões"),
    "DAGGER": ("Daggers", "Adagas"),
    "DAGGERPAIR": ("Dagger Pairs", "Pares de Adagas"),
    "CLAWPAIR": ("Claws", "Garras"),
    "BLOODLETTER": ("Bloodletters", "Sangradores"),
    "DUALSICKLE": ("Dual Sickles", "Foices Duplas"),
    "RAPIER": ("Rapiers", "Floretes"),
    "BOW": ("Bows", "Arcos"),
    "LONGBOW": ("Longbows", "Arcos Longos"),
    "WARBOW": ("Warbows", "Arcos de Guerra"),
    "CROSSBOW": ("Crossbows", "Bestas"),
    "CROSSBOWLARGE": ("Heavy Crossbows", "Bestas Pesadas"),
    "DUALCROSSBOW": ("Dual Crossbows", "Bestas Duplas"),
    "REPEATINGCROSSBOW": ("Crossbows", "Bestas"),
    "1HCROSSBOW": ("Crossbows", "Bestas"),
    "FIRESTAFF": ("Fire Staffs", "Cajados de Fogo"),
    "INFERNOSTAFF": ("Infernal Staffs", "Cajados Infernais"),
    "WILDFIRESTAFF": ("Wildfire Staffs", "Cajados de Fogo Selvagem"),
    "FROSTSTAFF": ("Frost Staffs", "Cajados de Gelo"),
    "GLACIALSTAFF": ("Glacial Staffs", "Cajados Glaciais"),
    "ICICLESTAFF": ("Icicle Staffs", "Cajados de Estalactite"),
    "HOLYSTAFF": ("Holy Staffs", "Cajados Sagrados"),
    "DIVINESTAFF": ("Divine Staffs", "Cajados Divinos"),
    "LIFETOUCHSTAFF": ("Lifetouch Staffs", "Cajados do Toque da Vida"),
    "NATURESTAFF": ("Nature Staffs", "Cajados da Natureza"),
    "WILDSTAFF": ("Wild Staffs", "Cajados Selvagens"),
    "ARCANESTAFF": ("Arcane Staffs", "Cajados Arcanos"),
    "ENIGMATICSTAFF": ("Enigmatic Staffs", "Cajados Enigmáticos"),
    "ARCANE": ("Arcane Staffs", "Cajados Arcanos"),
    "CURSEDSTAFF": ("Cursed Staffs", "Cajados Amaldiçoados"),
    "DEMONICSTAFF": ("Demonic Staffs", "Cajados Demoníacos"),
    "QUARTERSTAFF": ("Quarterstaffs", "Cajados de Combate"),
    "IRONCLADEDSTAFF": ("Iron-clad Staffs", "Cajados Encouraçados"),
    "DOUBLEBLADEDSTAFF": ("Double-bladed Staffs", "Cajados de Lâmina Dupla"),
    "BLACKMONKSTAFF": ("Black Monk Staffs", "Cajados do Monge Negro"),
    "COMBATSTAFF": ("Quarterstaffs", "Cajados de Combate"),
    "SHIELD": ("Shields", "Escudos"),
    "TOWERSHIELD": ("Tower Shields", "Escudos Torre"),
    "SPIKEDSHIELD": ("Spiked Shields", "Escudos com Espinhos"),
    "TORCH": ("Torches", "Tochas"),
    "BOOK": ("Tomes", "Tomos"),
    "TOME": ("Tomes", "Tomos"),
    "ORB": ("Orbs", "Orbes"),
    "ENIGMATICORB": ("Orbs", "Orbes"),
    "HORN": ("Horns", "Chifres"),
    "TOTEM": ("Totems", "Totens"),
    "CENSER": ("Censers", "Incensários"),
    "DEMONSKULL": ("Demon Skulls", "Crânios Demoníacos"),
    "KNUCKLES": ("Knuckles", "Soqueiras"),
    "IRONGAUNTLETS": ("Knuckles", "Soqueiras"),
    "ICEGAUNTLETS": ("Knuckles", "Soqueiras"),
    "SHAPESHIFTER": ("Shapeshifter Staffs", "Cajados Metamorfos"),
    "DUALSCIMITAR": ("Dual Scimitars", "Cimitarras Duplas"),
    "SCIMITAR": ("Scimitars", "Cimitarras"),
    "ROCKMACE": ("Maces", "Maças"),
    "ROCKSTAFF": ("Quarterstaffs", "Cajados de Combate"),
    "TWINSCYTHE": ("Scythes", "Foices"),
    "TALISMAN": ("Talismans", "Talismãs"),
    "SKULLORB": ("Orbs", "Orbes"),
    "FIRE": ("Fire Staffs", "Cajados de Fogo"),
    "ICECRYSTAL": ("Frost Staffs", "Cajados de Gelo"),
    "LAMP": ("Lamps", "Lâmpadas"),
    "JESTERCANE": ("Jester Canes", "Bengalas de Bobo"),
    "RAM": ("Battle Rams", "Aríetes"),
    "BLOODLETTER": ("Bloodletters", "Sangradores"),
    "ARTEFACT": ("Artefacts", "Artefatos"),
    "TOOL": ("Tools", "Ferramentas"),
    "OTHER": ("Other", "Outros"),
}

# Noisy / alias family tokens → canonical key
_FAMILY_ALIASES: Dict[str, str] = {
    "1HCROSSBOW": "CROSSBOW",
    "REPEATINGCROSSBOW": "CROSSBOW",
    "BOOK": "TOME",
    "ARCANE": "ARCANESTAFF",
    "FIRE": "FIRESTAFF",
    "COMBATSTAFF": "QUARTERSTAFF",
    "ENIGMATICORB": "ORB",
    "SKULLORB": "ORB",
    "ICECRYSTAL": "FROSTSTAFF",
    "IRONGAUNTLETS": "KNUCKLES",
    "ICEGAUNTLETS": "KNUCKLES",
    "ROCKMACE": "MACE",
    "ROCKSTAFF": "QUARTERSTAFF",
    "TWINSCYTHE": "SCYTHE",
    "CARVINGAXE": "CARVING",
}

_ARMOR_SLOT_NAMES = {
    "HEAD": ("Head", "Cabeça"),
    "ARMOR": ("Armor", "Armadura"),
    "SHOES": ("Shoes", "Sapatos"),
}
_ARMOR_MAT_NAMES = {
    "CLOTH": ("Cloth", "Tecido"),
    "LEATHER": ("Leather", "Couro"),
    "PLATE": ("Plate", "Placas"),
    "GATHERER": ("Gatherer", "Coletor"),
}

_ACCESSORY_NAMES = {
    "BAG": ("Bags", "Bolsas"),
    "CAPE": ("Capes", "Capas"),
    "MOUNT": ("Mounts", "Montarias"),
    "OTHER": ("Other", "Outros"),
}

_CONSUMABLE_NAMES = {
    "POTION": ("Potions", "Poções"),
    "MEAL": ("Meals", "Refeições"),
    "FOOD": ("Food", "Comida"),
    "OTHER": ("Other", "Outros"),
}

_GENERIC = {"ARTEFACT": ("Artefacts", "Artefatos"), "OTHER": ("Other", "Outros")}


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


def is_vanity_or_junk(unique: str) -> bool:
    """Skins, furniture, journals, vanity, unlock tokens, tools, non-gameplay UNIQUE_."""
    u = unique.upper()
    if u.startswith("SKIN_") or "FURNITUREITEM" in u or "FURNITURE" in u:
        return True
    if "_JOURNAL_" in u or u.startswith("JOURNAL_"):
        return True
    if "VANITY" in u or "UNLOCK_" in u:
        return True
    if u.startswith("UNIQUE_"):
        return True
    # Gathering / tracking tools — not equipment tabs by default
    if re.search(r"(^|_)TOOL(_|$)", u):
        return True
    # Farm / decoration / avatar fluff often mis-tagged
    if any(
        tok in u
        for tok in (
            "AVATAR",
            "LOOTCHEST",
            "HIDEOUT",
            "NONTRADABLE",
            "NON_TRADABLE",
            "ADC_",
            "TELLAFRIEND",
        )
    ):
        return True
    return False


def classify_unique(unique: str, *, include_vanity: bool = True) -> Optional[ItemType]:
    """Heuristic item type from UniqueName. Returns None for untyped/other.

    When include_vanity is False, vanity/tools/junk are not classified into tabs.
    Index build keeps include_vanity=True and filters at query time via meta flag.
    """
    u = unique.upper()

    if not include_vanity and is_vanity_or_junk(unique):
        return None

    # Always skip pure skins / furniture / journals from typed indexes when
    # not including vanity (also skip from default classify for skins etc.)
    if u.startswith("SKIN_") or "FURNITUREITEM" in u or "_JOURNAL_" in u:
        if not include_vanity:
            return None
        # Even with vanity, skins/furniture/journals stay out of equipment tabs
        return None

    # Consumables (token-aware FOOD to avoid furniture/false positives)
    if "POTION" in u or "_MEAL_" in u or u.startswith("MEAL_"):
        return "consumable"
    if re.search(r"(^|_)FOOD(_|$)", u) and "FURNITURE" not in u:
        return "consumable"

    # Armor slots (path tokens) — before weapon so ARTEFACT_HEAD_* etc. land here
    if re.search(r"(^|_)(HEAD|ARMOR|SHOES)_", u):
        return "armor"

    # Weapons (MAIN/2H/OFF) — tools already gated by include_vanity above
    if re.search(r"(^|_)(2H|MAIN|OFF)_", u):
        return "weapon"
    # Artefact weapons without MAIN/2H/OFF still start with ARTEFACT_2H_ etc.
    if "ARTEFACT" in u and re.search(r"(^|_)(2H|MAIN|OFF)_", u):
        return "weapon"

    # Accessories — token-aware to avoid CABBAGE / MOUNTAIN false positives
    if re.search(r"(^|_)BAG(?:_|@|$)", u) or re.search(r"^T\d+_BAG(?:@\d+)?$", u):
        return "accessory"
    if "CAPE" in u:
        return "accessory"
    if re.search(r"(^|_)MOUNT_", u) and "MOUNTUPGRADE" not in u:
        return "accessory"

    return None


def _pick_name(pair: tuple[str, str], lang: Lang) -> str:
    return pair[1] if lang == "pt_br" else pair[0]


def _normalize_family(family: str) -> str:
    family = family.upper()
    # Strip leading hand prefixes glued into the token (1HCROSSBOW)
    if family.startswith("1H") and len(family) > 2:
        alt = family[2:]
        if alt in _WEAPON_FAMILY_NAMES or alt in _FAMILY_ALIASES:
            family = alt
    if family.startswith("2H") and len(family) > 2:
        alt = family[2:]
        if alt in _WEAPON_FAMILY_NAMES or alt in _FAMILY_ALIASES:
            family = alt
    return _FAMILY_ALIASES.get(family, family)


def _weapon_family(unique: str) -> tuple[str, str]:
    """Return (category_key, english_fallback) — localized later via key."""
    u = unique.upper()
    if "ARTEFACT" in u:
        # Prefer grouping under Artefacts (clean UX); optional base family ignored
        return ("ARTEFACT", "Artefacts")

    base = strip_tier_enchant(u)
    m = re.search(r"(?:MAIN|2H|OFF)_(.+)$", base)
    if not m:
        return ("OTHER", "Other")

    rest = m.group(1)
    family = _normalize_family(rest.split("_")[0])
    pair = _WEAPON_FAMILY_NAMES.get(family)
    if pair:
        return (family, pair[0])
    # Title-case fallback without ugly glued tokens
    pretty = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", family.replace("_", " ").title())
    if not pretty.endswith("s"):
        pretty += "s"
    return (family, pretty)


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
        en = f"{_ARMOR_SLOT_NAMES[slot][0]} {_ARMOR_MAT_NAMES[mat][0]}"
        return (key, en)
    if slot:
        return (slot, _ARMOR_SLOT_NAMES[slot][0])
    return ("OTHER", "Other")


def _accessory_category(unique: str) -> tuple[str, str]:
    u = unique.upper()
    if re.search(r"(^|_)BAG(?:_|@|$)", u) or re.search(r"^T\d+_BAG(?:@\d+)?$", u):
        return ("BAG", "Bags")
    if "CAPE" in u:
        return ("CAPE", "Capes")
    if re.search(r"(^|_)MOUNT_", u):
        return ("MOUNT", "Mounts")
    return ("OTHER", "Other")


def _consumable_category(unique: str) -> tuple[str, str]:
    u = unique.upper()
    if "POTION" in u:
        return ("POTION", "Potions")
    if "_MEAL_" in u or u.startswith("MEAL_"):
        return ("MEAL", "Meals")
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


def localize_category_name(item_type: ItemType, category_key: str, fallback: str, lang: Lang) -> str:
    key = category_key.upper()
    if item_type == "weapon":
        pair = _WEAPON_FAMILY_NAMES.get(key) or _GENERIC.get(key)
        if pair:
            return _pick_name(pair, lang)
        return fallback if lang == "en_us" else fallback
    if item_type == "armor":
        if key == "ARTEFACT":
            return _pick_name(_GENERIC["ARTEFACT"], lang)
        if "_" in key:
            slot, mat = key.split("_", 1)
            if slot in _ARMOR_SLOT_NAMES and mat in _ARMOR_MAT_NAMES:
                if lang == "pt_br":
                    return f"{_ARMOR_SLOT_NAMES[slot][1]} {_ARMOR_MAT_NAMES[mat][1]}"
                return f"{_ARMOR_SLOT_NAMES[slot][0]} {_ARMOR_MAT_NAMES[mat][0]}"
        if key in _ARMOR_SLOT_NAMES:
            return _pick_name(_ARMOR_SLOT_NAMES[key], lang)
        if key in _GENERIC:
            return _pick_name(_GENERIC[key], lang)
        return fallback
    if item_type == "accessory":
        pair = _ACCESSORY_NAMES.get(key) or _GENERIC.get(key)
        if pair:
            return _pick_name(pair, lang)
        return fallback
    pair = _CONSUMABLE_NAMES.get(key) or _GENERIC.get(key)
    if pair:
        return _pick_name(pair, lang)
    return fallback


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
# (type, category_id) -> category meta
_CATEGORIES: Dict[ItemType, Dict[int, dict]] = {
    "weapon": {},
    "armor": {},
    "accessory": {},
    "consumable": {},
}


def _tier_sort_key(meta: dict) -> tuple:
    """Tier descending, then localized-independent unique name ascending."""
    t = meta.get("tier")
    try:
        tier_num = int(t) if t is not None else -1
    except (TypeError, ValueError):
        tier_num = -1
    return (-tier_num, meta["unique"])


def _build_indexes() -> None:
    for registro in ALBION_ITEMS:
        unique = registro.get("UniqueName")
        if not unique:
            continue
        # Build typed indexes including vanity so include_vanity=true can serve them;
        # skins/furniture/journals stay out entirely (never useful in equipment tabs).
        item_type = classify_unique(unique, include_vanity=True)
        if item_type is None:
            continue

        cat_key, cat_name = category_for(unique, item_type)
        cat_id = category_id_for(item_type, cat_key)
        iid = item_id_for(unique)
        tier = parse_tier(unique)
        vanity = is_vanity_or_junk(unique)
        is_tier0 = tier is None or tier == "0"

        meta = {
            "unique": unique,
            "type": item_type,
            "tier": tier,
            "category_id": cat_id,
            "category_key": cat_key,
            "vanity": vanity,
            "is_tier0": is_tier0,
            "registro": registro,
        }
        _META[unique] = meta
        _ID_TO_UNIQUE[iid] = unique
        _TYPED[item_type].append(meta)

        if cat_id not in _CATEGORIES[item_type]:
            _CATEGORIES[item_type][cat_id] = {
                "id": cat_id,
                "name": cat_name,  # English fallback stored; localized at list time
                "type": item_type,
                "subcategories": [],
                "_key": cat_key,
            }

    for t in _TYPED:
        _TYPED[t].sort(key=_tier_sort_key)


_build_indexes()


def list_categories(item_type: ItemType, lang: Lang = "pt_br", *, include_vanity: bool = False) -> List[dict]:
    lang = "pt_br" if lang not in ("pt_br", "en_us") else lang
    # Only expose categories that still have at least one visible item
    used_ids = set()
    for meta in _TYPED[item_type]:
        if not include_vanity and (meta["vanity"] or meta["is_tier0"]):
            continue
        used_ids.add(meta["category_id"])

    cats = [c for c in _CATEGORIES[item_type].values() if c["id"] in used_ids]
    localized = []
    for c in cats:
        name = localize_category_name(item_type, c["_key"], c["name"], lang)
        localized.append(
            {"id": c["id"], "name": name, "type": c["type"], "subcategories": c["subcategories"]}
        )
    localized.sort(key=lambda c: c["name"])
    return localized


def list_items(
    item_type: ItemType,
    *,
    tier: Optional[int] = None,
    category_id: Optional[int] = None,
    q: Optional[str] = None,
    lang: Lang = "pt_br",
    limit: int = 200,
    offset: int = 0,
    include_vanity: bool = False,
) -> List[dict]:
    lang = "pt_br" if lang not in ("pt_br", "en_us") else lang
    limit = max(1, min(limit, 1000))
    offset = max(0, offset)

    q_norm = normalizar(q) if q else ""
    results: List[dict] = []

    for meta in _TYPED[item_type]:
        if not include_vanity:
            if meta["vanity"]:
                continue
            # Default browse: drop tier 0 / untiered junk (unless caller asks tier=0)
            if meta["is_tier0"] and tier != 0:
                continue
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


def catalog_stats(*, include_vanity: bool = False) -> dict:
    out: Dict[str, int] = {}
    for t, items in _TYPED.items():
        if include_vanity:
            out[t] = len(items)
        else:
            out[t] = sum(1 for m in items if not m["vanity"] and not m["is_tier0"])
    return out


def count_items(item_type: ItemType, *, include_vanity: bool = False) -> int:
    if include_vanity:
        return len(_TYPED[item_type])
    return sum(1 for m in _TYPED[item_type] if not m["vanity"] and not m["is_tier0"])
