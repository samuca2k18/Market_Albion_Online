# app/routers/openalbion.py
"""OpenAlbion proxy routes with in-memory caching."""

import logging
import os
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import requests
from cachetools import TTLCache
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.models.schemas import CraftingResponseSchema, CraftingRowSchema

# Configuração de Logs estruturados
logger = logging.getLogger("albion_market")
_DEFAULT_LOG_FILE = Path("logs") / "openalbion.log"
_TMP_LOG_FILE = Path("/tmp") / "openalbion.log"


def _handler_exists(log_file: Path) -> bool:
    target = log_file.resolve()
    return any(
        isinstance(handler, RotatingFileHandler) and Path(handler.baseFilename) == target
        for handler in logger.handlers
    )


def _try_add_file_handler(log_file: Path) -> bool:
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        if _handler_exists(log_file):
            return True
        file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
        file_formatter = logging.Formatter('{"time":"%(asctime)s","level":"%(levelname)s","url":"%(message)s"}')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        return True
    except OSError:
        return False


_env_log_file = os.getenv("OPENALBION_LOG_FILE")
_candidate_paths = [Path(_env_log_file)] if _env_log_file else []
_candidate_paths.extend([_DEFAULT_LOG_FILE, _TMP_LOG_FILE])

for _candidate in _candidate_paths:
    if _try_add_file_handler(_candidate):
        break

PUBLIC_WINDOW_SECONDS = 60
PUBLIC_MAX_REQUESTS_PER_IP = 120
_public_hits: TTLCache = TTLCache(maxsize=20_000, ttl=PUBLIC_WINDOW_SECONDS)


def _public_rate_limit(request: Request) -> None:
    client_host = request.client.host if request.client else "unknown"
    key = f"{client_host}:{request.url.path}"
    current = int(_public_hits.get(key, 0)) + 1
    _public_hits[key] = current
    if current > PUBLIC_MAX_REQUESTS_PER_IP:
        raise HTTPException(429, "Muitas requisições. Tente novamente em instantes.")


router = APIRouter(
    prefix="/openalbion",
    tags=["OpenAlbion Proxy"],
    dependencies=[Depends(_public_rate_limit)],
)

OPENALBION_BASE = "https://api.openalbion.com/api/v3"

# TTLCache: expurga automaticamente entradas expiradas, evitando memory leak.
_cache: TTLCache = TTLCache(maxsize=500, ttl=3600)

DEFAULT_TTL = 3600


def _cached_get(url: str, params: dict | None = None, ttl: int = DEFAULT_TTL) -> Any:
    """HTTP GET with TTLCache e Error Handling robusto."""
    start_time = time.time()
    cache_key = f"{url}?{sorted((params or {}).items())}"

    if cache_key in _cache:
        return _cache[cache_key]

    try:
        response = requests.get(
            url,
            params=params,
            timeout=8,  # Reduzido para fail-fast
            headers={"Accept-Encoding": "gzip", "User-Agent": "AlbionMarket/1.0"},
        )
        response.raise_for_status()
        data = response.json()
        _cache[cache_key] = data
        
        duration = round(time.time() - start_time, 3)
        logger.info(f"{url} | status: {response.status_code} | time: {duration}s")
        
        return data
    except requests.exceptions.Timeout:
        logger.error(f"[OpenAlbion] Timeout em {url}")
        raise HTTPException(504, "A API externa demorou muito para responder. Tente novamente.")
    except requests.exceptions.ConnectionError:
        logger.error(f"[OpenAlbion] Falha de conexao/DNS em {url}")
        raise HTTPException(503, "Nao foi possivel conectar a base de dados do OpenAlbion.")
    except requests.RequestException as exc:
        status_code = exc.response.status_code if exc.response else 502
        logger.error(f"[OpenAlbion] Falha: {status_code} | URL: {url}")
        if cache_key in _cache:
            return _cache[cache_key]
        raise HTTPException(status_code, f"Erro na comunicacao com OpenAlbion.")


def _normalize_crafting_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize OpenAlbion consumable-craftings payload to legacy shape used by frontend.

    OpenAlbion docs currently return:
    data[].crafting.per_craft + data[].crafting.requirements[].identifier/value.
    """
    normalized_rows: list[dict[str, Any]] = []
    raw_rows = payload.get("data", []) if isinstance(payload, dict) else []

    for row in raw_rows:
        if not isinstance(row, dict):
            continue

        crafting = row.get("crafting") if isinstance(row.get("crafting"), dict) else row
        consumable = crafting.get("consumable") if isinstance(crafting.get("consumable"), dict) else {}
        requirements = crafting.get("requirements")
        if not isinstance(requirements, list):
            requirements = row.get("materials", [])

        materials: list[dict[str, Any]] = []
        for idx, req in enumerate(requirements):
            if not isinstance(req, dict):
                continue
            amount = req.get("value")
            if amount is None:
                amount = req.get("amount", 0)
            materials.append(
                {
                    "id": req.get("id", idx),
                    "amount": amount,
                    "item_id": req.get("item_id"),
                    "resource": req.get("identifier") or req.get("resource") or "",
                    "name": req.get("name"),
                    "icon": req.get("icon"),
                }
            )

        normalized_rows.append(
            {
                "id": crafting.get("id", row.get("id")),
                "yield_amount": crafting.get("per_craft", row.get("yield_amount", 1)),
                "item_id": consumable.get("id", row.get("item_id")),
                "category_id": row.get("category_id"),
                "enchantment": crafting.get("enchantment", row.get("enchantment", 0)),
                "materials": materials,
                "consumable": {
                    "id": consumable.get("id"),
                    "name": consumable.get("name"),
                    "identifier": consumable.get("identifier"),
                    "tier": consumable.get("tier"),
                    "item_power": consumable.get("item_power"),
                    "icon": consumable.get("icon"),
                }
                if consumable
                else None,
            }
        )

    return CraftingResponseSchema(data=normalized_rows)


def _query_filters(
    category_id: int | None = None,
    subcategory_id: int | None = None,
    tier: int | None = None,
) -> dict[str, int]:
    params: dict[str, int] = {}
    if category_id is not None:
        params["category_id"] = category_id
    if subcategory_id is not None:
        params["subcategory_id"] = subcategory_id
    if tier is not None:
        params["tier"] = tier
    return params


@router.get("/categories")
def get_categories(type: str | None = Query(None, description="weapon, armor, accessory, consumable")):
    params: dict[str, str] = {}
    if type:
        params["type"] = type
    return _cached_get(f"{OPENALBION_BASE}/categories", params)


@router.get("/weapons")
def get_weapons(
    category_id: int | None = Query(None),
    subcategory_id: int | None = Query(None),
    tier: int | None = Query(None),
):
    return _cached_get(f"{OPENALBION_BASE}/weapons", _query_filters(category_id, subcategory_id, tier))


@router.get("/armors")
def get_armors(
    category_id: int | None = Query(None),
    subcategory_id: int | None = Query(None),
    tier: int | None = Query(None),
):
    return _cached_get(f"{OPENALBION_BASE}/armors", _query_filters(category_id, subcategory_id, tier))


@router.get("/accessories")
def get_accessories(
    category_id: int | None = Query(None),
    subcategory_id: int | None = Query(None),
    tier: int | None = Query(None),
):
    return _cached_get(f"{OPENALBION_BASE}/accessories", _query_filters(category_id, subcategory_id, tier))


@router.get("/consumables")
def get_consumables(
    category_id: int | None = Query(None),
    subcategory_id: int | None = Query(None),
    tier: int | None = Query(None),
):
    return _cached_get(f"{OPENALBION_BASE}/consumables", _query_filters(category_id, subcategory_id, tier))


@router.get("/weapon-stats")
def get_weapon_stats(weapon_id: int = Query(...)):
    return _cached_get(f"{OPENALBION_BASE}/weapon-stats/weapon/{weapon_id}")


@router.get("/weapon-stats/weapon/{weapon_id}")
def get_weapon_stats_by_path(weapon_id: int):
    return _cached_get(f"{OPENALBION_BASE}/weapon-stats/weapon/{weapon_id}")


@router.get("/armor-stats")
def get_armor_stats(armor_id: int = Query(...)):
    return _cached_get(f"{OPENALBION_BASE}/armor-stats/armor/{armor_id}")


@router.get("/armor-stats/armor/{armor_id}")
def get_armor_stats_by_path(armor_id: int):
    return _cached_get(f"{OPENALBION_BASE}/armor-stats/armor/{armor_id}")


@router.get("/accessory-stats")
def get_accessory_stats(accessory_id: int = Query(...)):
    return _cached_get(f"{OPENALBION_BASE}/accessory-stats/accessory/{accessory_id}")


@router.get("/accessory-stats/accessory/{accessory_id}")
def get_accessory_stats_by_path(accessory_id: int):
    return _cached_get(f"{OPENALBION_BASE}/accessory-stats/accessory/{accessory_id}")


@router.get("/consumable-stats")
def get_consumable_stats(consumable_id: int = Query(...)):
    return _cached_get(f"{OPENALBION_BASE}/consumable-stats/consumable/{consumable_id}")


@router.get("/consumable-stats/consumable/{consumable_id}")
def get_consumable_stats_by_path(consumable_id: int):
    return _cached_get(f"{OPENALBION_BASE}/consumable-stats/consumable/{consumable_id}")


@router.get("/spells")
def get_spells(
    item_id: int = Query(..., description="ID numerico do item no OpenAlbion"),
    item_type: str = Query("weapon", description="weapon, armor ou accessory"),
):
    if item_type not in {"weapon", "armor", "accessory"}:
        raise HTTPException(400, "item_type invalido. Use weapon, armor ou accessory")
    return _cached_get(f"{OPENALBION_BASE}/spells/{item_type}/{item_id}")


@router.get("/spells/{item_type}/{item_id}")
def get_spells_by_path(item_type: str, item_id: int):
    if item_type not in {"weapon", "armor", "accessory"}:
        raise HTTPException(400, "item_type invalido. Use weapon, armor ou accessory")
    return _cached_get(f"{OPENALBION_BASE}/spells/{item_type}/{item_id}")


@router.get("/consumable-craftings", response_model=CraftingResponseSchema)
def get_consumable_craftings(consumable_id: int = Query(...)):
    raw = _cached_get(f"{OPENALBION_BASE}/consumable-craftings/consumable/{consumable_id}")
    return _normalize_crafting_payload(raw)


@router.get("/consumable-craftings/consumable/{consumable_id}", response_model=CraftingResponseSchema)
def get_consumable_craftings_by_path(consumable_id: int):
    raw = _cached_get(f"{OPENALBION_BASE}/consumable-craftings/consumable/{consumable_id}")
    return _normalize_crafting_payload(raw)


@router.get("/item-detail/{item_type}/{item_id}")
def item_detail(item_type: str, item_id: int):
    """
    Aggregated item data including base payload, stats and spells (when available).
    item_type: weapon, armor, accessory, consumable
    """
    type_map = {
        "weapon": {
            "base": "weapons",
            "stats": f"{OPENALBION_BASE}/weapon-stats/weapon/{item_id}",
            "spells": f"{OPENALBION_BASE}/spells/weapon/{item_id}",
        },
        "armor": {
            "base": "armors",
            "stats": f"{OPENALBION_BASE}/armor-stats/armor/{item_id}",
            "spells": f"{OPENALBION_BASE}/spells/armor/{item_id}",
        },
        "accessory": {
            "base": "accessories",
            "stats": f"{OPENALBION_BASE}/accessory-stats/accessory/{item_id}",
            "spells": f"{OPENALBION_BASE}/spells/accessory/{item_id}",
        },
        "consumable": {
            "base": "consumables",
            "stats": f"{OPENALBION_BASE}/consumable-stats/consumable/{item_id}",
            "spells": None,
        },
    }

    config = type_map.get(item_type)
    if not config:
        raise HTTPException(400, f"Tipo invalido: {item_type}")

    result: dict[str, Any] = {"type": item_type, "id": item_id}

    try:
        base_data = _cached_get(f"{OPENALBION_BASE}/{config['base']}")
        items_list = base_data.get("data", []) if isinstance(base_data, dict) else []
        item = next((entry for entry in items_list if entry.get("id") == item_id), None)
        if item:
            result["item"] = item
    except Exception:
        pass

    stats_url = config["stats"]
    if stats_url:
        try:
            result["stats"] = _cached_get(stats_url)
        except Exception:
            pass

    spells_url = config["spells"]
    if spells_url:
        try:
            result["spells"] = _cached_get(spells_url)
        except Exception:
            pass

    return result
