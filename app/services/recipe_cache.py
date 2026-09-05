"""Aggressive recipe cache for Albion gameinfo craftingRequirements."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from cachetools import TTLCache

GAMEINFO_ITEM_URL = "https://gameinfo.albiononline.com/api/gameinfo/items/{unique}/data"

_REPO_ROOT = Path(__file__).resolve().parents[2]
DISK_CACHE_DIR = _REPO_ROOT / "app" / "data" / "recipe_cache"

_memory: TTLCache = TTLCache(maxsize=4000, ttl=60 * 60 * 24)  # 24h
_lock = threading.Lock()
_session = requests.Session()
_session.headers.update(
    {
        "Accept-Encoding": "gzip",
        "User-Agent": "AlbionMarketAPI/1.0",
    }
)

# Soft rate-limit between live gameinfo fetches
_last_fetch_ts = 0.0
_MIN_FETCH_GAP_S = 0.12


def _disk_path(unique_name: str) -> Path:
    safe = unique_name.replace("/", "_").replace("\\", "_").upper()
    return DISK_CACHE_DIR / f"{safe}.json"


def _read_disk(unique_name: str) -> Optional[dict]:
    path = _disk_path(unique_name)
    if not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _write_disk(unique_name: str, payload: dict) -> None:
    try:
        DISK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = _disk_path(unique_name)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
    except Exception:
        pass


def _normalize_materials(craft_resource_list: Any) -> List[Dict[str, Any]]:
    materials: List[Dict[str, Any]] = []
    if not isinstance(craft_resource_list, list):
        return materials
    for row in craft_resource_list:
        if not isinstance(row, dict):
            continue
        unique = (row.get("uniqueName") or row.get("unique_name") or "").strip()
        count = row.get("count") or row.get("Count") or 0
        try:
            count_i = int(count)
        except (TypeError, ValueError):
            continue
        if not unique or count_i <= 0:
            continue
        materials.append({"unique_name": unique.upper(), "count": count_i})
    return materials


def _extract_craft_block(block: Any) -> Optional[dict]:
    if not isinstance(block, dict):
        return None
    materials = _normalize_materials(block.get("craftResourceList") or block.get("craft_resource_list"))
    if not materials:
        return None
    focus = block.get("craftingFocus")
    if focus is None:
        focus = block.get("crafting_focus")
    silver = block.get("silver", 0) or 0
    try:
        focus_f = float(focus) if focus is not None else None
    except (TypeError, ValueError):
        focus_f = None
    try:
        silver_f = float(silver)
    except (TypeError, ValueError):
        silver_f = 0.0
    return {
        "focus_cost": focus_f,
        "silver": silver_f,
        "materials": materials,
        "time": block.get("time"),
    }


def parse_recipes_from_gameinfo(payload: dict, unique_name: str) -> List[dict]:
    """
    Return list of normalized recipes for base + enchantments.
    Each: { unique_name, enchant, focus_cost, silver, materials, time }
    """
    base_unique = unique_name.upper().split("@")[0]
    recipes: List[dict] = []

    base_block = payload.get("craftingRequirements") or payload.get("craftingrequirements")
    base = _extract_craft_block(base_block)
    if base:
        recipes.append(
            {
                "unique_name": base_unique,
                "enchant": 0,
                **base,
            }
        )

    enc_root = payload.get("enchantments") or {}
    enc_list = enc_root.get("enchantments") if isinstance(enc_root, dict) else None
    if isinstance(enc_list, list):
        for enc in enc_list:
            if not isinstance(enc, dict):
                continue
            level = enc.get("enchantmentLevel", enc.get("enchantment_level", 0))
            try:
                level_i = int(level)
            except (TypeError, ValueError):
                continue
            craft = _extract_craft_block(enc.get("craftingRequirements") or enc.get("craftingrequirements"))
            if not craft:
                continue
            recipes.append(
                {
                    "unique_name": f"{base_unique}@{level_i}",
                    "enchant": level_i,
                    **craft,
                }
            )

    return recipes


def _fetch_live(unique_name: str) -> Optional[dict]:
    global _last_fetch_ts
    with _lock:
        gap = time.time() - _last_fetch_ts
        if gap < _MIN_FETCH_GAP_S:
            time.sleep(_MIN_FETCH_GAP_S - gap)
        _last_fetch_ts = time.time()

    url = GAMEINFO_ITEM_URL.format(unique=unique_name.upper().split("@")[0])
    try:
        resp = _session.get(url, timeout=12)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def get_item_payload(unique_name: str, *, force_refresh: bool = False) -> Optional[dict]:
    key = unique_name.upper().split("@")[0]
    if not force_refresh:
        cached = _memory.get(key)
        if cached is not None:
            return cached
        disk = _read_disk(key)
        if disk is not None:
            _memory[key] = disk
            return disk

    payload = _fetch_live(key)
    if payload is None:
        return None
    _memory[key] = payload
    _write_disk(key, payload)
    return payload


def get_recipe(unique_name: str, *, force_refresh: bool = False) -> Optional[dict]:
    """
    Return a single normalized recipe matching unique_name (with optional @enchant).
    """
    raw = unique_name.strip().upper()
    if not raw:
        return None
    base = raw.split("@")[0]
    enchant = 0
    if "@" in raw:
        try:
            enchant = int(raw.split("@", 1)[1])
        except ValueError:
            enchant = 0

    payload = get_item_payload(base, force_refresh=force_refresh)
    if not payload:
        return None

    recipes = parse_recipes_from_gameinfo(payload, base)
    for recipe in recipes:
        if recipe["enchant"] == enchant:
            return recipe
    # Fallback: if asking for base and only enchanted exist, no match
    return None


def get_all_recipes_for_item(unique_name: str) -> List[dict]:
    base = unique_name.upper().split("@")[0]
    payload = get_item_payload(base)
    if not payload:
        return []
    return parse_recipes_from_gameinfo(payload, base)


def cache_stats() -> dict:
    return {
        "memory_size": len(_memory),
        "disk_dir": str(DISK_CACHE_DIR),
        "disk_files": len(list(DISK_CACHE_DIR.glob("*.json"))) if DISK_CACHE_DIR.is_dir() else 0,
    }
