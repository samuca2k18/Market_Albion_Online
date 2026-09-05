"""Local catalog API (nomes_*.json + albion_index). Replaces OpenAlbion for browsing."""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query

from app.utils import catalog_index as idx

ItemType = Literal["weapon", "armor", "accessory", "consumable"]
Lang = Literal["pt_br", "en_us"]

router = APIRouter(prefix="/catalog", tags=["Catalog"])

_VALID_TYPES = {"weapon", "armor", "accessory", "consumable"}


def _parse_type(value: str) -> ItemType:
    if value not in _VALID_TYPES:
        raise HTTPException(400, f"type invalido: {value}. Use weapon|armor|accessory|consumable")
    return value  # type: ignore[return-value]


def _parse_lang(lang: str) -> Lang:
    return "en_us" if lang == "en_us" else "pt_br"


@router.get("/categories")
def get_categories(
    type: str = Query(..., description="weapon, armor, accessory, consumable"),
    lang: str = Query("pt_br", description="pt_br | en_us"),
    include_vanity: bool = Query(
        False,
        description="Include vanity/skins/tools/junk categories (default false)",
    ),
):
    item_type = _parse_type(type)
    return {
        "data": idx.list_categories(
            item_type,
            lang=_parse_lang(lang),
            include_vanity=include_vanity,
        )
    }


@router.get("/items")
def get_items(
    type: str = Query(..., description="weapon, armor, accessory, consumable"),
    tier: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    subcategory_id: Optional[int] = Query(None, description="Ignored (no subcategories in MVP)"),
    q: Optional[str] = Query(None, description="Search by name or UniqueName"),
    lang: str = Query("pt_br", description="pt_br | en_us"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    include_vanity: bool = Query(
        False,
        description="Include tier-0 / vanity / tools / UNIQUE junk (default false)",
    ),
):
    del subcategory_id  # accepted for API compatibility; unused
    item_type = _parse_type(type)
    return {
        "data": idx.list_items(
            item_type,
            tier=tier,
            category_id=category_id,
            q=q,
            lang=_parse_lang(lang),
            limit=limit,
            offset=offset,
            include_vanity=include_vanity,
        )
    }


def _items_alias(
    item_type: ItemType,
    category_id: Optional[int],
    subcategory_id: Optional[int],
    tier: Optional[int],
    q: Optional[str],
    lang: str,
    limit: int,
    offset: int,
    include_vanity: bool,
):
    del subcategory_id
    return {
        "data": idx.list_items(
            item_type,
            tier=tier,
            category_id=category_id,
            q=q,
            lang=_parse_lang(lang),
            limit=limit,
            offset=offset,
            include_vanity=include_vanity,
        )
    }


@router.get("/weapons")
def get_weapons(
    category_id: Optional[int] = Query(None),
    subcategory_id: Optional[int] = Query(None),
    tier: Optional[int] = Query(None),
    q: Optional[str] = Query(None),
    lang: str = Query("pt_br"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    include_vanity: bool = Query(False),
):
    return _items_alias(
        "weapon", category_id, subcategory_id, tier, q, lang, limit, offset, include_vanity
    )


@router.get("/armors")
def get_armors(
    category_id: Optional[int] = Query(None),
    subcategory_id: Optional[int] = Query(None),
    tier: Optional[int] = Query(None),
    q: Optional[str] = Query(None),
    lang: str = Query("pt_br"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    include_vanity: bool = Query(False),
):
    return _items_alias(
        "armor", category_id, subcategory_id, tier, q, lang, limit, offset, include_vanity
    )


@router.get("/accessories")
def get_accessories(
    category_id: Optional[int] = Query(None),
    subcategory_id: Optional[int] = Query(None),
    tier: Optional[int] = Query(None),
    q: Optional[str] = Query(None),
    lang: str = Query("pt_br"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    include_vanity: bool = Query(False),
):
    return _items_alias(
        "accessory", category_id, subcategory_id, tier, q, lang, limit, offset, include_vanity
    )


@router.get("/consumables")
def get_consumables(
    category_id: Optional[int] = Query(None),
    subcategory_id: Optional[int] = Query(None),
    tier: Optional[int] = Query(None),
    q: Optional[str] = Query(None),
    lang: str = Query("pt_br"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    include_vanity: bool = Query(False),
):
    return _items_alias(
        "consumable", category_id, subcategory_id, tier, q, lang, limit, offset, include_vanity
    )


@router.get("/item-detail/{item_type}/{item_id}")
def item_detail(
    item_type: str,
    item_id: int,
    lang: str = Query("pt_br"),
):
    parsed = _parse_type(item_type)
    meta = idx.get_meta_by_id(item_id)
    if not meta or meta["type"] != parsed:
        # Still try to resolve by id ignoring type mismatch for resilience
        item = idx.get_item_by_id(item_id, _parse_lang(lang))
        if not item:
            raise HTTPException(404, f"Item {item_id} nao encontrado")
        return {
            "type": parsed,
            "id": item_id,
            "item": item,
            "stats": {"data": []},
            "spells": {"data": []},
        }

    item = idx.to_api_item(meta["registro"], _parse_lang(lang))
    return {
        "type": parsed,
        "id": item_id,
        "item": item,
        "stats": {"data": []},
        "spells": {"data": []},
    }


@router.get("/consumable-craftings")
def consumable_craftings(consumable_id: int = Query(...)):
    """Stub — richer crafting deferred. Empty list so Crafting page fails gracefully."""
    del consumable_id
    return {"data": []}


@router.get("/stats")
def catalog_stats(
    include_vanity: bool = Query(False),
):
    """Debug/ops: counts per typed catalog."""
    return {"data": idx.catalog_stats(include_vanity=include_vanity)}
