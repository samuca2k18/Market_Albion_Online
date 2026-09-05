"""Real craft calculator — recipes from gameinfo + market prices."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.limiter import limiter
from app.dependencies import get_current_user
from app.services import recipe_cache
from app.utils.albion_client import get_prices
from app.utils.albion_index import ITEM_BY_UNIQUE
from app.utils import catalog_index

router = APIRouter(prefix="/craft", tags=["Crafting"])

ROYAL_CITIES = [
    "Bridgewatch",
    "Martlock",
    "Thetford",
    "Lymhurst",
    "Fort Sterling",
    "Caerleon",
    "Brecilien",
]

BLACK_MARKET = "Black Market"

VALID_REGIONS = {"west", "europe", "east"}


def _validate_region(region: str) -> str:
    r = (region or "west").lower().strip()
    if r not in VALID_REGIONS:
        raise HTTPException(400, f"Região inválida. Use: {', '.join(sorted(VALID_REGIONS))}")
    return r


def _item_names(unique_name: str) -> Dict[str, str]:
    reg = ITEM_BY_UNIQUE.get(unique_name.upper()) or ITEM_BY_UNIQUE.get(unique_name.upper().split("@")[0])
    if not reg:
        return {"name_pt": unique_name, "name_en": unique_name}
    return {
        "name_pt": reg.get("PT-BR") or unique_name,
        "name_en": reg.get("EN-US") or unique_name,
    }


def _normalize_city(city: str) -> str:
    c = (city or "").strip()
    if not c:
        return ""
    key = c.lower().replace("_", " ").replace("-", " ")
    key = " ".join(key.split())
    aliases = {
        "black market": BLACK_MARKET,
        "blackmarket": BLACK_MARKET,
        "bm": BLACK_MARKET,
        "bridgewatch": "Bridgewatch",
        "martlock": "Martlock",
        "thetford": "Thetford",
        "lymhurst": "Lymhurst",
        "fort sterling": "Fort Sterling",
        "fortsterling": "Fort Sterling",
        "caerleon": "Caerleon",
        "brecilien": "Brecilien",
    }
    return aliases.get(key, c)


def _parse_price_date(raw: Any) -> Optional[datetime]:
    if not raw:
        return None
    try:
        s = str(raw).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _age_hours(dt: Optional[datetime]) -> Optional[float]:
    if not dt:
        return None
    return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0)


def _pick_sell_price(rows: List[dict], city: str, item_id: str, quality: Optional[int] = None) -> dict:
    """Best (lowest) sell_price_min for item in city."""
    city_n = _normalize_city(city)
    item_u = item_id.upper()
    best = None
    for row in rows:
        if (row.get("item_id") or "").upper() != item_u:
            continue
        if _normalize_city(row.get("city", "")) != city_n:
            continue
        if quality is not None and int(row.get("quality") or 1) != quality:
            continue
        price = row.get("sell_price_min") or 0
        if price <= 0:
            continue
        if best is None or price < best["price"]:
            best = {
                "price": float(price),
                "date": row.get("sell_price_min_date") or "",
                "quality": int(row.get("quality") or 1),
            }
    return best or {"price": None, "date": "", "quality": quality or 1}


def _pick_buy_price(rows: List[dict], city: str, item_id: str, quality: Optional[int] = None) -> dict:
    """Best (highest) buy_price_max for item in city — used for Black Market."""
    city_n = _normalize_city(city)
    item_u = item_id.upper()
    best = None
    for row in rows:
        if (row.get("item_id") or "").upper() != item_u:
            continue
        if _normalize_city(row.get("city", "")) != city_n:
            continue
        if quality is not None and int(row.get("quality") or 1) != quality:
            continue
        price = row.get("buy_price_max") or 0
        if price <= 0:
            continue
        if best is None or price > best["price"]:
            best = {
                "price": float(price),
                "date": row.get("buy_price_max_date") or "",
                "quality": int(row.get("quality") or 1),
            }
    return best or {"price": None, "date": "", "quality": quality or 1}


def _serialize_recipe(recipe: dict) -> dict:
    names = _item_names(recipe["unique_name"])
    materials = []
    for mat in recipe.get("materials") or []:
        mnames = _item_names(mat["unique_name"])
        materials.append(
            {
                "unique_name": mat["unique_name"],
                "count": mat["count"],
                "name_pt": mnames["name_pt"],
                "name_en": mnames["name_en"],
            }
        )
    return {
        "unique_name": recipe["unique_name"],
        "enchant": recipe.get("enchant", 0),
        "focus_cost": recipe.get("focus_cost"),
        "silver": recipe.get("silver", 0),
        "time": recipe.get("time"),
        "materials": materials,
        "name_pt": names["name_pt"],
        "name_en": names["name_en"],
    }


@router.get("/recipe/{unique_name}")
@limiter.limit("60/minute")
def get_craft_recipe(request: Request, unique_name: str):
    """Normalized crafting recipe from gameinfo (cached)."""
    recipe = recipe_cache.get_recipe(unique_name)
    if not recipe:
        raise HTTPException(404, "Receita não encontrada para este item.")
    return _serialize_recipe(recipe)


@router.get("/profit")
@limiter.limit("40/minute")
def craft_profit(
    request: Request,
    item: str = Query(..., description="UniqueName do produto (ex: T4_MAIN_SWORD)"),
    city_buy: str = Query("Caerleon", description="Cidade para comprar materiais"),
    city_sell: str = Query("Caerleon", description="Cidade/BM para vender o produto"),
    region: str = Query("west", description="west / europe / east"),
    focus_return_pct: float = Query(0, ge=0, le=100),
    journal_bonus_pct: float = Query(0, ge=0, le=100),
    market_tax_pct: Optional[float] = Query(None, ge=0, le=20),
    crafting_fee: float = Query(0, ge=0),
    quality: Optional[int] = Query(None, ge=1, le=5),
    current_user=Depends(get_current_user),
):
    """
    Compute craft profit for one item.
    Black Market sell uses buy_price_max and defaults tax to 0.
    """
    region = _validate_region(region)
    city_buy_n = _normalize_city(city_buy)
    city_sell_n = _normalize_city(city_sell)
    item_id = item.strip().upper()

    recipe = recipe_cache.get_recipe(item_id)
    if not recipe:
        raise HTTPException(404, "Receita não encontrada para este item.")

    is_bm = city_sell_n == BLACK_MARKET
    # BM into buy-order typically has 0 market tax
    if market_tax_pct is None:
        tax_pct = 0.0 if is_bm else 6.5
    else:
        tax_pct = float(market_tax_pct)

    tax_note = (
        "Black Market: imposto de venda padrão 0% (venda em buy-order)."
        if is_bm and market_tax_pct is None
        else None
    )

    mat_ids = [m["unique_name"] for m in recipe["materials"]]
    locations = list({city_buy_n, city_sell_n})
    qualities = [quality] if quality else None

    # Materials: sell orders in city_buy
    mat_rows = get_prices(mat_ids, locations=[city_buy_n], qualities=qualities, region=region, mode="sell")
    # Product: sell in city markets, buy orders on BM
    product_mode = "buy" if is_bm else "sell"
    product_rows = get_prices(
        [item_id],
        locations=[city_sell_n],
        qualities=qualities,
        region=region,
        mode=product_mode if is_bm else "any",
    )

    material_breakdown = []
    dates: List[datetime] = []
    raw_material_cost = 0.0
    missing_materials = False

    for mat in recipe["materials"]:
        picked = _pick_sell_price(mat_rows, city_buy_n, mat["unique_name"], quality)
        unit = picked["price"]
        total = (unit * mat["count"]) if unit is not None else None
        if unit is None:
            missing_materials = True
        else:
            raw_material_cost += total  # type: ignore[operator]
            dt = _parse_price_date(picked["date"])
            if dt:
                dates.append(dt)
        mnames = _item_names(mat["unique_name"])
        material_breakdown.append(
            {
                "unique_name": mat["unique_name"],
                "count": mat["count"],
                "unit_price": unit,
                "total_cost": total,
                "price_date": picked["date"] or None,
                "name_pt": mnames["name_pt"],
                "name_en": mnames["name_en"],
            }
        )

    if is_bm:
        sell_picked = _pick_buy_price(product_rows, city_sell_n, item_id, quality)
    else:
        sell_picked = _pick_sell_price(product_rows, city_sell_n, item_id, quality)

    sell_price = sell_picked["price"]
    if sell_picked["date"]:
        dt = _parse_price_date(sell_picked["date"])
        if dt:
            dates.append(dt)

    focus_mult = max(0.0, 1.0 - focus_return_pct / 100.0)
    journal_mult = max(0.0, 1.0 - journal_bonus_pct / 100.0)
    effective_cost = raw_material_cost * focus_mult * journal_mult + crafting_fee

    net_revenue = None
    profit = None
    roi = None
    silver_per_focus = None

    if sell_price is not None:
        net_revenue = sell_price * (1.0 - tax_pct / 100.0)
        if not missing_materials:
            profit = net_revenue - effective_cost
            if effective_cost > 0:
                roi = (profit / effective_cost) * 100.0
            focus_cost = recipe.get("focus_cost")
            if focus_cost and focus_cost > 0 and profit is not None:
                silver_per_focus = profit / focus_cost

    ages = [_age_hours(d) for d in dates if d]
    data_age_hours = max(ages) if ages else None

    names = _item_names(item_id)

    return {
        "item": item_id,
        "name_pt": names["name_pt"],
        "name_en": names["name_en"],
        "enchant": recipe.get("enchant", 0),
        "region": region,
        "city_buy": city_buy_n,
        "city_sell": city_sell_n,
        "is_black_market": is_bm,
        "focus_return_pct": focus_return_pct,
        "journal_bonus_pct": journal_bonus_pct,
        "market_tax_pct": tax_pct,
        "tax_note": tax_note,
        "crafting_fee": crafting_fee,
        "quality": quality,
        "focus_cost": recipe.get("focus_cost"),
        "recipe_silver": recipe.get("silver", 0),
        "materials": material_breakdown,
        "raw_material_cost": None if missing_materials else round(raw_material_cost),
        "effective_cost": None if missing_materials else round(effective_cost),
        "sell_price": None if sell_price is None else round(sell_price),
        "sell_price_date": sell_picked["date"] or None,
        "sell_price_kind": "buy_price_max" if is_bm else "sell_price_min",
        "net_revenue": None if net_revenue is None else round(net_revenue),
        "profit": None if profit is None else round(profit),
        "roi": None if roi is None else round(roi, 2),
        "silver_per_focus": None if silver_per_focus is None else round(silver_per_focus, 2),
        "data_age_hours": None if data_age_hours is None else round(data_age_hours, 2),
        "missing_prices": missing_materials or sell_price is None,
    }


def _curated_craft_candidates(limit: int = 300) -> List[str]:
    """T4–T8 weapons + armor unique names (base, no enchant), capped."""
    seen = set()
    out: List[str] = []
    for item_type in ("weapon", "armor"):
        for tier in range(4, 9):
            rows = catalog_index.list_items(item_type, tier=tier, limit=1000, offset=0)
            for row in rows:
                unique = (row.get("unique_name") or row.get("identifier") or "").upper()
                if not unique or "@" in unique:
                    continue
                if unique in seen:
                    continue
                # Prefer craftable gear prefixes
                if not any(
                    token in unique
                    for token in (
                        "_MAIN_",
                        "_2H_",
                        "_OFF_",
                        "_HEAD_",
                        "_ARMOR_",
                        "_SHOES_",
                    )
                ):
                    continue
                seen.add(unique)
                out.append(unique)
                if len(out) >= limit:
                    return out
    return out


@router.get("/top")
@limiter.limit("15/minute")
def craft_top(
    request: Request,
    city_buy: str = Query("Caerleon"),
    city_sell: str = Query("Caerleon"),
    region: str = Query("west"),
    focus_return_pct: float = Query(0, ge=0, le=100),
    journal_bonus_pct: float = Query(0, ge=0, le=100),
    market_tax_pct: Optional[float] = Query(None, ge=0, le=20),
    crafting_fee: float = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    scan_limit: int = Query(200, ge=20, le=400),
    sort_by: str = Query("profit", description="profit | roi | silver_per_focus"),
    current_user=Depends(get_current_user),
):
    """
    Scan a curated set of T4–T8 weapons/armor, return top N crafts by profit.
    Builds recipe cache progressively; skips items without recipe.
    """
    region = _validate_region(region)
    city_buy_n = _normalize_city(city_buy)
    city_sell_n = _normalize_city(city_sell)
    is_bm = city_sell_n == BLACK_MARKET
    if market_tax_pct is None:
        tax_pct = 0.0 if is_bm else 6.5
    else:
        tax_pct = float(market_tax_pct)

    candidates = _curated_craft_candidates(scan_limit)
    results: List[dict] = []
    scanned = 0
    with_recipe = 0

    # Prefetch recipes (rate-limited inside recipe_cache)
    recipes_map: Dict[str, dict] = {}
    all_mat_ids: List[str] = []
    for item_id in candidates:
        scanned += 1
        recipe = recipe_cache.get_recipe(item_id)
        if not recipe:
            continue
        with_recipe += 1
        recipes_map[item_id] = recipe
        for mat in recipe["materials"]:
            all_mat_ids.append(mat["unique_name"])

    if not recipes_map:
        return {
            "region": region,
            "city_buy": city_buy_n,
            "city_sell": city_sell_n,
            "scanned": scanned,
            "with_recipe": 0,
            "cache": recipe_cache.cache_stats(),
            "items": [],
        }

    unique_mats = list(dict.fromkeys(all_mat_ids))
    product_ids = list(recipes_map.keys())

    # Batch prices
    mat_rows: List[dict] = []
    for i in range(0, len(unique_mats), 80):
        chunk = unique_mats[i : i + 80]
        mat_rows.extend(
            get_prices(chunk, locations=[city_buy_n], region=region, mode="sell")
        )

    product_mode = "buy" if is_bm else "sell"
    product_rows: List[dict] = []
    for i in range(0, len(product_ids), 80):
        chunk = product_ids[i : i + 80]
        product_rows.extend(
            get_prices(
                chunk,
                locations=[city_sell_n],
                region=region,
                mode="any" if not is_bm else "buy",
            )
        )

    focus_mult = max(0.0, 1.0 - focus_return_pct / 100.0)
    journal_mult = max(0.0, 1.0 - journal_bonus_pct / 100.0)

    for item_id, recipe in recipes_map.items():
        dates: List[datetime] = []
        raw_cost = 0.0
        missing = False
        for mat in recipe["materials"]:
            picked = _pick_sell_price(mat_rows, city_buy_n, mat["unique_name"])
            if picked["price"] is None:
                missing = True
                break
            raw_cost += picked["price"] * mat["count"]
            dt = _parse_price_date(picked["date"])
            if dt:
                dates.append(dt)
        if missing:
            continue

        if is_bm:
            sell_picked = _pick_buy_price(product_rows, city_sell_n, item_id)
        else:
            sell_picked = _pick_sell_price(product_rows, city_sell_n, item_id)
        if sell_picked["price"] is None:
            continue
        dt = _parse_price_date(sell_picked["date"])
        if dt:
            dates.append(dt)

        effective = raw_cost * focus_mult * journal_mult + crafting_fee
        net = sell_picked["price"] * (1.0 - tax_pct / 100.0)
        profit = net - effective
        roi = (profit / effective) * 100.0 if effective > 0 else 0.0
        focus_cost = recipe.get("focus_cost")
        spf = (profit / focus_cost) if focus_cost and focus_cost > 0 else None
        ages = [_age_hours(d) for d in dates if d]
        data_age = max(ages) if ages else None
        names = _item_names(item_id)

        results.append(
            {
                "item": item_id,
                "name_pt": names["name_pt"],
                "name_en": names["name_en"],
                "enchant": recipe.get("enchant", 0),
                "focus_cost": focus_cost,
                "raw_material_cost": round(raw_cost),
                "effective_cost": round(effective),
                "sell_price": round(sell_picked["price"]),
                "net_revenue": round(net),
                "profit": round(profit),
                "roi": round(roi, 2),
                "silver_per_focus": None if spf is None else round(spf, 2),
                "data_age_hours": None if data_age is None else round(data_age, 2),
            }
        )

    sort_key = sort_by if sort_by in {"profit", "roi", "silver_per_focus"} else "profit"

    def _sort_val(row: dict) -> float:
        v = row.get(sort_key)
        return float(v) if isinstance(v, (int, float)) else float("-inf")

    results.sort(key=_sort_val, reverse=True)

    return {
        "region": region,
        "city_buy": city_buy_n,
        "city_sell": city_sell_n,
        "is_black_market": is_bm,
        "market_tax_pct": tax_pct,
        "focus_return_pct": focus_return_pct,
        "journal_bonus_pct": journal_bonus_pct,
        "scanned": scanned,
        "with_recipe": with_recipe,
        "sort_by": sort_key,
        "cache": recipe_cache.cache_stats(),
        "items": results[:limit],
    }
