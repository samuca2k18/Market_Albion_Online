from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests as req
from cachetools import TTLCache
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.limiter import limiter
from app.dependencies import get_current_user, get_db
from app.models import UserItem
from app.core.config import settings
from app.utils.albion_client import get_prices, get_price_history, get_gold_prices
from app.utils.albion_index import ALBION_ITEMS, buscar_item_por_nome

router = APIRouter(prefix="/albion", tags=["Albion Online"])


LANG_SLUG_TO_KEY = {"pt-br": "pt_br", "en-us": "en_us"}

REGIONS = [
    {"id": "europe", "label": "Europe", "flag": "🌍", "host": "europe.albion-online-data.com"},
    {"id": "west",   "label": "Americas", "flag": "🌎", "host": "west.albion-online-data.com"},
    {"id": "east",   "label": "Asia",     "flag": "🌏", "host": "east.albion-online-data.com"},
]

GAMEINFO_BASE_URL = "https://gameinfo.albiononline.com/api/gameinfo"

CITY_ALIASES = {
    "bridgewatch": "Bridgewatch",
    "martlock": "Martlock",
    "thetford": "Thetford",
    "lymhurst": "Lymhurst",
    "fort sterling": "Fort Sterling",
    "fortsterling": "Fort Sterling",
    "caerleon": "Caerleon",
    "brecilien": "Brecilien",
}

DEFAULT_CITY_FALLBACK = [
    "Bridgewatch",
    "Martlock",
    "Thetford",
    "Lymhurst",
    "Fort Sterling",
    "Caerleon",
]

ITEM_WEIGHT_CACHE: TTLCache = TTLCache(maxsize=5000, ttl=60 * 60 * 12)


def _validate_region(region: str) -> str:
    valid = [r["id"] for r in REGIONS]
    if region not in valid:
        raise HTTPException(400, f"Região inválida. Use: {', '.join(valid)}")
    return region


@router.get("/regions")
def list_regions():
    """
    Retorna as regiões de servidor disponíveis (sem autenticação).
    """
    return REGIONS


def _normalize_city_name(raw_city: str) -> str:
    city = (raw_city or "").strip()
    if not city:
        return ""
    key = city.lower().replace("_", " ").replace("-", " ")
    key = " ".join(key.split())
    return CITY_ALIASES.get(key, city)


def _parse_cities(cities_raw: str | None, fallback: List[str] | None = None) -> List[str]:
    raw = [c.strip() for c in (cities_raw or "").split(",") if c.strip()]
    if not raw:
        raw = fallback or settings.DEFAULT_CITIES or DEFAULT_CITY_FALLBACK
    normalized = [_normalize_city_name(city) for city in raw]
    # Remove duplicados sem perder ordem
    seen = set()
    unique: List[str] = []
    for city in normalized:
        if city and city not in seen:
            seen.add(city)
            unique.append(city)
    return unique


def _gameinfo_get(path: str, params: dict | None = None) -> Any:
    try:
        response = req.get(
            f"{GAMEINFO_BASE_URL}{path}",
            params=params,
            timeout=12,
            headers={
                "Accept-Encoding": "gzip",
                "User-Agent": "AlbionMarketAPI/1.0",
            },
        )
        response.raise_for_status()
        return response.json()
    except req.RequestException as exc:
        status_code = exc.response.status_code if exc.response else 502
        if status_code == 404:
            raise HTTPException(404, "Recurso não encontrado na API pública do Albion.")
        raise HTTPException(502, "Falha ao consultar API pública do Albion.")


def _item_base_id(item_id: str) -> str:
    return (item_id or "").upper().split("@")[0].strip()


def _normalize_item_list(items: List[str]) -> List[str]:
    normalized = [_item_base_id(item_id) for item_id in items if item_id]
    return list(dict.fromkeys([item_id for item_id in normalized if item_id]))


def _coerce_weight(value: Any) -> float | None:
    try:
        weight = float(value)
        if weight > 0:
            return round(weight, 3)
    except (TypeError, ValueError):
        return None
    return None


def _extract_weight_from_payload(payload: Any) -> float | None:
    if isinstance(payload, dict):
        for key in ("Weight", "weight", "ItemWeight", "item_weight"):
            found = _coerce_weight(payload.get(key))
            if found:
                return found

        nested = payload.get("data")
        if nested is not None:
            return _extract_weight_from_payload(nested)

    if isinstance(payload, list):
        for entry in payload:
            found = _extract_weight_from_payload(entry)
            if found:
                return found

    return None


def _estimate_weight_from_item_id(item_id: str) -> float | None:
    base_id = _item_base_id(item_id)
    if not base_id:
        return None

    token = base_id.split("_", 1)[1] if "_" in base_id else base_id

    if token.startswith(("RUNE", "SOUL", "RELIC", "ESSENCE")):
        return 0.1
    if token.startswith(("POTION", "MEAL", "OMELETTE", "SOUP", "SALAD", "PIE", "SANDWICH")):
        return 0.4
    if token.startswith(("BAG", "CAPE")):
        return 1.0
    if token.startswith(("FIBER", "HIDE", "ORE", "ROCK", "WOOD")):
        return 2.0
    if token.startswith(("CLOTH", "LEATHER", "METALBAR", "PLANKS", "STONEBLOCK")):
        return 1.5
    if token.startswith(("2H_", "MAIN_", "OFF_", "HEAD_", "ARMOR_", "SHOES_")):
        return 3.0
    if "MOUNT" in token:
        return 30.0

    return None


def _resolve_item_weight(item_id: str, default_weight: float) -> tuple[float, str]:
    base_id = _item_base_id(item_id)
    if not base_id:
        return max(default_weight, 0.01), "default"

    cached = ITEM_WEIGHT_CACHE.get(base_id)
    if cached:
        return cached

    try:
        payload = _gameinfo_get(f"/items/{base_id}/data")
        payload_weight = _extract_weight_from_payload(payload)
        if payload_weight:
            ITEM_WEIGHT_CACHE[base_id] = (payload_weight, "gameinfo")
            return payload_weight, "gameinfo"
    except HTTPException:
        pass

    heuristic_weight = _estimate_weight_from_item_id(base_id)
    if heuristic_weight:
        ITEM_WEIGHT_CACHE[base_id] = (heuristic_weight, "heuristic")
        return heuristic_weight, "heuristic"

    return max(default_weight, 0.01), "default"


def _simplify_kill_event(event: dict) -> dict:
    killer = event.get("Killer", {}) or {}
    victim = event.get("Victim", {}) or {}

    killer_weapon = killer.get("Equipment", {}).get("MainHand")
    victim_weapon = victim.get("Equipment", {}).get("MainHand")

    return {
        "event_id": event.get("EventId"),
        "timestamp": event.get("TimeStamp"),
        "kill_area": event.get("KillArea", "UNKNOWN"),
        "total_fame": event.get("TotalVictimKillFame", 0),
        "participants": event.get("numberOfParticipants", 1),
        "killer": {
            "id": killer.get("Id"),
            "name": killer.get("Name", "Unknown"),
            "guild_id": killer.get("GuildId"),
            "guild": killer.get("GuildName", ""),
            "alliance_id": killer.get("AllianceId"),
            "alliance": killer.get("AllianceName", ""),
            "ip": round(killer.get("AverageItemPower", 0)),
            "weapon": killer_weapon.get("Type") if killer_weapon else None,
        },
        "victim": {
            "id": victim.get("Id"),
            "name": victim.get("Name", "Unknown"),
            "guild_id": victim.get("GuildId"),
            "guild": victim.get("GuildName", ""),
            "alliance_id": victim.get("AllianceId"),
            "alliance": victim.get("AllianceName", ""),
            "ip": round(victim.get("AverageItemPower", 0)),
            "weapon": victim_weapon.get("Type") if victim_weapon else None,
            "death_fame": victim.get("DeathFame", 0),
        },
    }


@router.get("/cities")
def list_cities():
    """
    Lista de cidades suportadas para consulta de mercado.
    """
    return _parse_cities(None)


@router.get("/unique-items")
@limiter.limit("60/minute")
def list_unique_items(
    request: Request,
    q: str | None = Query(None, min_length=2, description="Filtro opcional por nome/unique"),
    limit: int = Query(200, ge=1, le=2000),
):
    """
    Retorna catálogo de itens (UniqueName + nomes PT/EN) para autocomplete local.
    """
    query = (q or "").strip().lower()
    rows = ALBION_ITEMS
    if query:
        rows = [
            item
            for item in ALBION_ITEMS
            if query in (item.get("UniqueName", "").lower())
            or query in (item.get("PT-BR", "").lower())
            or query in (item.get("EN-US", "").lower())
        ]
    serialized = [
        {
            "unique_name": item.get("UniqueName", ""),
            "name_pt": item.get("PT-BR", ""),
            "name_en": item.get("EN-US", ""),
        }
        for item in rows[:limit]
    ]
    return serialized


def _validate_lang_slug(lang: str) -> str:
    key = LANG_SLUG_TO_KEY.get(lang.lower())
    if not key:
        raise HTTPException(400, "Idioma inválido, use pt-br ou en-us")
    return key


def _serialize_resultados(resultados: List[dict]):
    return [
        {
            "unique_name": r["UniqueName"],
            "name_pt": r.get("PT-BR", ""),
            "name_en": r.get("EN-US", ""),
            "matched": r.get("__matched", ""),
        }
        for r in resultados
    ]


def _normalize_lang(lang: str) -> str:
    lang_norm = (lang or "").lower().replace("-", "_")
    return lang_norm if lang_norm in ("pt_br", "en_us") else "pt_br"


@router.get("/search/pt-br")
@limiter.limit("80/minute")
def search_item_pt(request: Request, q: str = Query(..., min_length=2)):
    """
    Busca itens por nome em PT-BR usando o índice nomes_pt_br.json.
    """
    resultados = buscar_item_por_nome(q, "pt_br")
    return _serialize_resultados(resultados)


@router.get("/search/en-us")
@limiter.limit("80/minute")
def search_item_en(request: Request, q: str = Query(..., min_length=2)):
    """
    Busca itens por nome em EN-US usando o índice nomes_en_us.json.
    """
    resultados = buscar_item_por_nome(q, "en_us")
    return _serialize_resultados(resultados)


# Rota legada mantida para compatibilidade (usa PT-BR por padrão)
@router.get("/search")
@limiter.limit("80/minute")
def search_item(request: Request, q: str = Query(..., min_length=2)):
    # Mantém compatibilidade aceitando PT-BR e, em fallback, EN-US
    resultados = buscar_item_por_nome(q, "pt_br")
    if not resultados:
        resultados = buscar_item_por_nome(q, "en_us")
    return _serialize_resultados(resultados)


def _resolver_lista_itens(
    raw_items: List[str], lang_key: str, permitir_fallback_en: bool = False
) -> List[str]:
    """
    Resolve nomes humanos para UniqueName respeitando o idioma.
    """
    resolved: List[str] = []
    for it in raw_items:
        if it.upper().startswith("T") and "_" in it:
            resolved.append(it.upper())
            continue

        candidatos = buscar_item_por_nome(it, lang_key)
        if not candidatos and permitir_fallback_en and lang_key == "pt_br":
            candidatos = buscar_item_por_nome(it, "en_us")
        if candidatos:
            resolved.append(candidatos[0]["UniqueName"])
    return resolved


def _buscar_precos_por_idioma(
    items: str,
    cities: str,
    qualities: str,
    lang_key: str,
    current_user,
    permitir_fallback_en: bool = False,
    region: str = "europe",
):
    raw_items = [i.strip() for i in items.split(",") if i.strip()]
    item_list = _resolver_lista_itens(
        raw_items, lang_key, permitir_fallback_en=permitir_fallback_en
    )

    if not item_list:
        raise HTTPException(404, "Nenhum item válido encontrado")

    city_list = _parse_cities(cities)
    quality_list = [int(q) for q in qualities.split(",") if q.strip()]

    data = get_prices(item_list, city_list, quality_list, region=region)
    if not data:
        raise HTTPException(404, "Nenhum preço encontrado")

    # Retorna o mais barato por item
    cheapest_by_item = {}
    for d in data:
        item_id = d["item_id"]
        if (
            item_id not in cheapest_by_item
            or d["sell_price_min"] < cheapest_by_item[item_id]["price"]
        ):
            cheapest_by_item[item_id] = {
                "city": d["city"],
                "price": d["sell_price_min"],
                "quality": d["quality"],
                "enchantment": d.get("enchantment", 0),
                "updated": d["sell_price_min_date"],
                "region": region,
            }

    return {"items": cheapest_by_item, "all_data": data, "region": region}


@router.get("/prices/pt-br")
@limiter.limit("45/minute")
def get_prices_pt(
    request: Request,
    items: str = Query(
        ...,
        description="Itens separados por vírgula (UniqueNames OU nomes PT-BR)",
    ),
    cities: str = Query(",".join(settings.DEFAULT_CITIES)),
    qualities: str = Query("1,2,3,4,5"),
    region: str = Query("europe", description="Região do servidor: europe, west (Américas) ou east (Ásia)"),
    current_user=Depends(get_current_user),
):
    """
    Preços para múltiplos itens resolvendo nomes PT-BR.
    """
    _validate_region(region)
    return _buscar_precos_por_idioma(items, cities, qualities, "pt_br", current_user, region=region)


@router.get("/prices/en-us")
@limiter.limit("45/minute")
def get_prices_en(
    request: Request,
    items: str = Query(
        ...,
        description="Itens separados por vírgula (UniqueNames OU nomes EN-US)",
    ),
    cities: str = Query(",".join(settings.DEFAULT_CITIES)),
    qualities: str = Query("1,2,3,4,5"),
    region: str = Query("europe", description="Região do servidor: europe, west (Américas) ou east (Ásia)"),
    current_user=Depends(get_current_user),
):
    """
    Preços para múltiplos itens resolvendo nomes EN-US.
    """
    _validate_region(region)
    return _buscar_precos_por_idioma(items, cities, qualities, "en_us", current_user, region=region)


@router.get("/prices")
@limiter.limit("45/minute")
def get_prices_endpoint(
    request: Request,
    items: str = Query(
        ...,
        description="Itens separados por vírgula (UniqueNames OU nomes PT/EN)",
    ),
    cities: str = Query(",".join(settings.DEFAULT_CITIES)),
    qualities: str = Query("1,2,3,4,5"),
    region: str = Query("europe", description="Região do servidor: europe, west (Américas) ou east (Ásia)"),
    current_user=Depends(get_current_user),
):
    """
    Preços para múltiplos itens (legado, usa PT-BR como padrão).

    Aceita:
      - UniqueNames: T4_BAG,T4_BAG@1
      - Nomes humanos: 'bolsa do adepto, capa letal'
    Faz a resolução de nomes PT/EN -> UniqueName automaticamente.
    """
    _validate_region(region)
    return _buscar_precos_por_idioma(
        items, cities, qualities, "pt_br", current_user, permitir_fallback_en=True, region=region
    )


@router.get("/price-by-name")
@limiter.limit("60/minute")
def price_by_name(
    request: Request,
    name: str = Query(..., description="Nome em PT-BR ou EN"),
    cities: str = Query(",".join(settings.DEFAULT_CITIES)),
    region: str = Query("europe", description="Região do servidor"),
    current_user=Depends(get_current_user),
):
    """
    Preço para um único item a partir de nome humano (PT/EN).
    """
    return _preco_por_nome(name, cities, "pt_br", permitir_fallback_en=True, region=region)


def _preco_por_nome(
    name: str, cities: str, lang_key: str, permitir_fallback_en: bool = False, region: str = "europe"
):
    itens = buscar_item_por_nome(name, lang_key)
    if not itens and permitir_fallback_en and lang_key == "pt_br":
        itens = buscar_item_por_nome(name, "en_us")
    if not itens:
        raise HTTPException(404, "Item não encontrado")

    unique = itens[0]["UniqueName"]
    city_list = _parse_cities(cities)
    _validate_region(region)
    data = get_prices([unique], city_list, region=region)

    if not data:
        raise HTTPException(404, "Sem preços disponíveis no momento")

    cheapest = min(data, key=lambda x: x["sell_price_min"])

    return {
        "searched": name,
        "item_found": unique,
        "name_pt": itens[0].get("PT-BR", ""),
        "name_en": itens[0].get("EN-US", ""),
        "cheapest_city": cheapest["city"],
        "price": cheapest["sell_price_min"],
        "quality": cheapest["quality"],
        "updated_at": cheapest["sell_price_min_date"],
        "region": region,
        "all_prices": data[:10],
    }


@router.get("/price-by-name/pt-br")
@limiter.limit("60/minute")
def price_by_name_pt(
    request: Request,
    name: str = Query(..., description="Nome em PT-BR"),
    cities: str = Query(",".join(settings.DEFAULT_CITIES)),
    region: str = Query("europe", description="Região do servidor"),
    current_user=Depends(get_current_user),
):
    return _preco_por_nome(name, cities, "pt_br", permitir_fallback_en=True, region=region)


@router.get("/price-by-name/en-us")
@limiter.limit("60/minute")
def price_by_name_en(
    request: Request,
    name: str = Query(..., description="Nome em EN-US"),
    cities: str = Query(",".join(settings.DEFAULT_CITIES)),
    region: str = Query("europe", description="Região do servidor"),
    current_user=Depends(get_current_user),
):
    return _preco_por_nome(name, cities, "en_us", region=region)


@router.get("/history/{item_id}")
@limiter.limit("40/minute")
def price_history(
    request: Request,
    item_id: str,
    days: int = Query(7, ge=1, le=30, description="Quantos dias de histórico"),
    cities: str = Query("Caerleon", description="Cidades separadas por vírgula"),
    resolution: str = Query("6h", description="1h, 6h ou 24h"),
    region: str = Query("europe", description="Região do servidor: europe, west (Américas) ou east (Ásia)"),
    current_user=Depends(get_current_user),
):
    """
    Histórico de preços para uso no gráfico do frontend.
    """
    _validate_region(region)
    city_list = _parse_cities(cities)

    history = get_price_history(
        item_id=item_id.upper(),
        locations=city_list,
        days=days,
        time_resolution=resolution,
        region=region,
    )

    # Se a API não devolver nada, não é erro de servidor, só "sem dados"
    if not history:
        return {
            "item": item_id,
            "cities": city_list,
            "resolution": resolution,
            "days": days,
            "region": region,
            "data": [],
        }

    return {
        "item": item_id,
        "cities": city_list,
        "resolution": resolution,
        "days": days,
        "region": region,
        "data": history,
    }


@router.get("/my-items-prices")
@limiter.limit("40/minute")
def my_items_prices(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    lang: str = Query(
        "pt_br",
        description="Idioma para resolver nomes não únicos (pt_br ou en_us)",
    ),
    region: str = Query("europe", description="Região do servidor: europe, west (Américas) ou east (Ásia)"),
):
    """
    Retorna os preços dos itens salvos pelo usuário.

    Se houver itens antigos salvos com nomes humanos (BOLSA, BAG),
    tenta resolver para UniqueName antes de chamar a API.
    """
    user_items = db.query(UserItem).filter(UserItem.user_id == current_user.id).all()
    raw_names = [item.item_name for item in user_items]
    display_map = {item.item_name.upper(): item.display_name for item in user_items}

    if not raw_names:
        return []

    lang_key = _normalize_lang(lang)
    resolved_names: List[str] = []
    for name in raw_names:
        if name.upper().startswith("T") and "_" in name:
            resolved_names.append(name.upper())
        else:
            candidatos = buscar_item_por_nome(name, lang_key)
            if not candidatos and lang_key == "pt_br":
                candidatos = buscar_item_por_nome(name, "en_us")
            if candidatos:
                resolved_names.append(candidatos[0]["UniqueName"])

    if not resolved_names:
        return []

    _validate_region(region)
    raw_data = get_prices(
        resolved_names,
        locations=_parse_cities(None),
        region=region,
    )

    result = []
    for entry in raw_data:
        if entry.get("sell_price_min", 0) <= 0:
            continue
        display_name = display_map.get(entry["item_id"].upper())
        result.append(
            {
                "item_name": entry["item_id"],  # sempre UniqueName aqui
                "display_name": display_name,
                "city": entry["city"],
                "price": entry["sell_price_min"],
                "quality": entry["quality"],
                "enchantment": entry.get("enchantment", 0),
                "updated_at": entry.get("sell_price_min_date", ""),
            }
        )

    # Ordena do mais barato pro mais caro
    result.sort(key=lambda x: x["price"])
    return result


@router.get("/gold")
@limiter.limit("40/minute")
def gold_prices(
    request: Request,
    count: int = Query(2, ge=1, le=1000),
    region: str = Query("europe", description="europe, west ou east"),
):
    """
    Retorna preços de ouro e variação opcional.
    """
    _validate_region(region)
    data = get_gold_prices(count=count, region=region)
    
    if not data:
        raise HTTPException(404, "Preços de ouro não disponíveis")
        
    current = data[0] if len(data) > 0 else None
    previous = data[1] if len(data) > 1 else None
    
    variation = 0
    if current and previous:
        variation = current["price"] - previous["price"]
        
    return {
        "current": current,
        "previous": previous,
        "variation": variation,
        "all": data,
        "region": region
    }
@router.get("/arbitrage")
@limiter.limit("25/minute")
def arbitrage_calculator(
    request: Request,
    items: List[str] = Query(None),
    region: str = Query("europe"),
    tax: float = Query(0.08, description="Imposto de mercado (0.04 ou 0.08)"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Calcula oportunidades de arbitragem entre cidades para uma lista de itens.
    Se nenhuma lista for fornecida, usa os itens rastreados do usuário.
    """
    _validate_region(region)
    
    # Se não passar itens, usa os itens rastreados do usuário
    if not items:
        user_items = db.query(UserItem).filter(UserItem.user_id == user.id).all()
        items = list(set([ui.item_name for ui in user_items]))
    
    if not items:
        return []

    # Busca preços em todas as cidades padrão
    # Limitando a 50 itens por vez para não estourar a URL/API
    all_opportunities: List[Dict[str, Any]] = []
    chunk_size = 50
    item_chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]  # pyre-ignore[16]
    
    setup_fee = 0.01  # 1% de taxa de setup de ordem de venda
    
    for chunk in item_chunks:
        prices = get_prices(
            items=chunk,
            locations=_parse_cities(None),
            region=region,
        )
        
        # Organiza por item e qualidade
        item_prices = {}
        for p in prices:
            item_id = p["item_id"]
            quality = p.get("quality", 1)
            key = (item_id, quality)
            
            if key not in item_prices:
                item_prices[key] = []
            item_prices[key].append(p)
            
        for (item_id, quality), city_prices in item_prices.items():
            # Compara cada par de cidades
            for buy_data in city_prices:
                buy_price = buy_data.get("sell_price_min", 0)
                if not buy_price or buy_price <= 0:
                    continue
                
                for sell_data in city_prices:
                    if buy_data["city"] == sell_data["city"]:
                        continue
                    
                    sell_price = sell_data.get("sell_price_min", 0)
                    if not sell_price or sell_price <= 0:
                        continue
                    
                    # Cálculo: Receita Líquida - Custo Total
                    cost = buy_price * (1 + setup_fee)
                    revenue = sell_price * (1 - tax)
                    profit = revenue - cost
                    
                    if profit > 0:
                        roi = (profit / cost) * 100
                        all_opportunities.append({
                            "item_id": item_id,
                            "quality": quality,
                            "buy_from": buy_data["city"],
                            "buy_price": buy_price,
                            "sell_at": sell_data["city"],
                            "sell_price": sell_price,
                            "profit": int(profit),
                            "roi": round(roi, 2),
                            "buy_date": buy_data["sell_price_min_date"],
                            "sell_date": sell_data["sell_price_min_date"]
                        })
    
    # Ordena por maior lucro absoluto
    all_opportunities.sort(key=lambda x: x["profit"], reverse=True)

    return all_opportunities[:100]  # pyre-ignore[16]


@router.get("/arbitrage-route")
@limiter.limit("20/minute")
def arbitrage_route_calculator(
    request: Request,
    origin: str = Query(..., description="Cidade de origem (compra)"),
    destination: str = Query(..., description="Cidade de destino (venda)"),
    items: List[str] = Query(None),
    region: str = Query("europe"),
    tax: float = Query(0.08, ge=0, le=0.25),
    setup_fee: float = Query(0.01, ge=0, le=0.1),
    mount_capacity: float = Query(1200, gt=0, description="Capacidade da montaria"),
    default_weight: float = Query(1.0, gt=0, description="Peso fallback por item"),
    max_results: int = Query(100, ge=10, le=300),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Calcula arbitragem de rota fixa (origem -> destino) com lucro por viagem.
    Inclui estimativa de quantidade transportÃ¡vel com base no peso dos itens.
    """
    _validate_region(region)

    origin_city = _normalize_city_name(origin)
    destination_city = _normalize_city_name(destination)
    if not origin_city or not destination_city:
        raise HTTPException(400, "Informe cidades vÃ¡lidas para origem e destino.")
    if origin_city == destination_city:
        raise HTTPException(400, "Origem e destino devem ser cidades diferentes.")

    requested_items = _normalize_item_list(items or [])
    if not requested_items:
        user_items = db.query(UserItem).filter(UserItem.user_id == user.id).all()
        requested_items = _normalize_item_list([ui.item_name for ui in user_items])

    if not requested_items:
        return {
            "region": region,
            "origin": origin_city,
            "destination": destination_city,
            "mount_capacity": mount_capacity,
            "default_weight": default_weight,
            "tax": tax,
            "setup_fee": setup_fee,
            "item_count_considered": 0,
            "weight_sources": {"gameinfo": 0, "heuristic": 0, "default": 0},
            "opportunities": [],
        }

    item_chunks = [
        requested_items[i:i + 80] for i in range(0, len(requested_items), 80)
    ]
    route_prices: Dict[tuple[str, int], Dict[str, Dict[str, Any]]] = {}

    for chunk in item_chunks:
        rows = get_prices(
            items=chunk,
            locations=[origin_city, destination_city],
            region=region,
        )
        for row in rows:
            item_id = _item_base_id(row.get("item_id", ""))
            city = _normalize_city_name(row.get("city", ""))
            quality = int(row.get("quality", 1) or 1)
            price = row.get("sell_price_min", 0)
            if not item_id or city not in {origin_city, destination_city}:
                continue
            if not isinstance(price, (int, float)) or price <= 0:
                continue

            city_map = route_prices.setdefault((item_id, quality), {})
            current = city_map.get(city)
            if not current or price < current["price"]:
                city_map[city] = {
                    "price": float(price),
                    "updated_at": row.get("sell_price_min_date", ""),
                }

    opportunities: List[Dict[str, Any]] = []
    weight_sources = Counter({"gameinfo": 0, "heuristic": 0, "default": 0})

    for (item_id, quality), city_map in route_prices.items():
        buy_data = city_map.get(origin_city)
        sell_data = city_map.get(destination_city)
        if not buy_data or not sell_data:
            continue

        buy_price = buy_data["price"]
        sell_price = sell_data["price"]
        unit_cost = buy_price * (1 + setup_fee)
        unit_revenue = sell_price * (1 - tax)
        unit_profit = unit_revenue - unit_cost

        if unit_profit <= 0:
            continue

        item_weight, weight_source = _resolve_item_weight(item_id, default_weight)
        weight_sources[weight_source] += 1

        max_units = int(mount_capacity // max(item_weight, 0.01))
        if max_units <= 0:
            continue

        total_weight = round(max_units * item_weight, 2)
        trip_profit = int(unit_profit * max_units)
        unit_roi = (unit_profit / unit_cost) * 100 if unit_cost > 0 else 0

        opportunities.append(
            {
                "item_id": item_id,
                "quality": quality,
                "buy_from": origin_city,
                "buy_price": int(buy_price),
                "sell_at": destination_city,
                "sell_price": int(sell_price),
                "unit_profit": int(unit_profit),
                "unit_roi": round(unit_roi, 2),
                "item_weight": item_weight,
                "weight_source": weight_source,
                "max_units_by_capacity": max_units,
                "total_weight": total_weight,
                "trip_profit": trip_profit,
                "investment_required": int(unit_cost * max_units),
                "buy_date": buy_data.get("updated_at", ""),
                "sell_date": sell_data.get("updated_at", ""),
            }
        )

    opportunities.sort(key=lambda row: row["trip_profit"], reverse=True)

    return {
        "region": region,
        "origin": origin_city,
        "destination": destination_city,
        "mount_capacity": mount_capacity,
        "default_weight": default_weight,
        "tax": tax,
        "setup_fee": setup_fee,
        "item_count_considered": len(requested_items),
        "weight_sources": {
            "gameinfo": weight_sources.get("gameinfo", 0),
            "heuristic": weight_sources.get("heuristic", 0),
            "default": weight_sources.get("default", 0),
        },
        "opportunities": opportunities[:max_results],
    }


@router.get("/bandit-event")
def bandit_event_status():
    """
    Retorna o status do próximo Bandit Event baseado no ciclo fixo de 2h.
    Os eventos Bandit acontecem em intervalos regulares com duração de ~20min.
    
    Futuramente pode ser aprimorado com dados do NATS em tempo real.
    """
    from datetime import datetime, timezone, timedelta
    
    now = datetime.now(timezone.utc)
    
    # Ciclo de 2h — anchor em um horário UTC conhecido
    cycle_minutes = 120
    event_duration_minutes = 20
    
    # Anchor: meia-noite UTC de hoje como referência (eventos a cada 2h: 00, 02, 04, ...)
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Calcular minutos desde a meia-noite
    elapsed_minutes = (now - today_midnight).total_seconds() / 60
    
    # Posição no ciclo atual
    cycle_position = elapsed_minutes % cycle_minutes
    
    if cycle_position < event_duration_minutes:
        # Evento ativo
        phase = 2
        minutes_remaining = event_duration_minutes - cycle_position
        event_time = now + timedelta(minutes=minutes_remaining)
        status = "active"
    elif cycle_position >= (cycle_minutes - 30):
        # Próximo em menos de 30 min
        minutes_until = cycle_minutes - cycle_position
        phase = 1
        event_time = now + timedelta(minutes=minutes_until)
        status = "soon"
    else:
        # Próximo evento distante
        minutes_until = cycle_minutes - cycle_position
        phase = 1
        event_time = now + timedelta(minutes=minutes_until)
        status = "waiting"
    
    return {
        "status": status,
        "phase": phase,
        "next_event_utc": event_time.isoformat(),
        "minutes_remaining": round(minutes_until if status != "active" else minutes_remaining),
        "cycle_minutes": cycle_minutes,
        "event_duration_minutes": event_duration_minutes,
    }


@router.get("/killboard")
@limiter.limit("30/minute")
def killboard_feed(
    request: Request,
    limit: int = Query(20, ge=1, le=51),
):
    """
    Proxy para a API pública de kills do Albion Online.
    Não requer autenticação do nosso backend.
    """
    events = _gameinfo_get("/events", {"limit": limit})
    return [_simplify_kill_event(ev) for ev in events]


@router.get("/player/search")
@limiter.limit("30/minute")
def player_search(
    request: Request,
    q: str = Query(..., min_length=2, description="Nome parcial do jogador"),
    limit: int = Query(15, ge=1, le=50),
):
    data = _gameinfo_get("/search", {"q": q})
    players = [row for row in data if row.get("Type") == "Player"][:limit]
    return [
        {
            "id": row.get("Id"),
            "name": row.get("Name"),
            "guild_name": row.get("GuildName"),
            "alliance_name": row.get("AllianceName"),
        }
        for row in players
    ]


@router.get("/guild/search")
@limiter.limit("30/minute")
def guild_search(
    request: Request,
    q: str = Query(..., min_length=2, description="Nome parcial da guilda"),
    limit: int = Query(15, ge=1, le=50),
):
    data = _gameinfo_get("/search", {"q": q})
    guilds = [row for row in data if row.get("Type") == "Guild"][:limit]
    return [
        {
            "id": row.get("Id"),
            "name": row.get("Name"),
            "alliance_name": row.get("AllianceName"),
            "member_count": row.get("MemberCount"),
        }
        for row in guilds
    ]


@router.get("/player/{player_id}")
@limiter.limit("30/minute")
def player_profile(request: Request, player_id: str):
    return _gameinfo_get(f"/players/{player_id}")


@router.get("/player/{player_id}/kills")
@limiter.limit("30/minute")
def player_kills(
    request: Request,
    player_id: str,
    limit: int = Query(20, ge=1, le=51),
    offset: int = Query(0, ge=0),
):
    events = _gameinfo_get(
        f"/players/{player_id}/kills",
        {"limit": limit, "offset": offset},
    )
    return [_simplify_kill_event(ev) for ev in events]


@router.get("/player/{player_id}/deaths")
@limiter.limit("30/minute")
def player_deaths(
    request: Request,
    player_id: str,
    limit: int = Query(20, ge=1, le=51),
    offset: int = Query(0, ge=0),
):
    events = _gameinfo_get(
        f"/players/{player_id}/deaths",
        {"limit": limit, "offset": offset},
    )
    return [_simplify_kill_event(ev) for ev in events]


@router.get("/guild/{guild_id}")
@limiter.limit("30/minute")
def guild_profile(request: Request, guild_id: str):
    return _gameinfo_get(f"/guilds/{guild_id}")


@router.get("/guild/{guild_id}/members")
@limiter.limit("30/minute")
def guild_members(request: Request, guild_id: str):
    return _gameinfo_get(f"/guilds/{guild_id}/members")


@router.get("/alliance/{alliance_id}")
@limiter.limit("30/minute")
def alliance_profile(request: Request, alliance_id: str):
    return _gameinfo_get(f"/alliances/{alliance_id}")


@router.get("/meta-market")
@limiter.limit("20/minute")
def meta_market(
    request: Request,
    region: str = Query("europe", description="europe, west ou east"),
    kill_limit: int = Query(40, ge=10, le=51),
    top_items: int = Query(12, ge=3, le=30),
    cities: str = Query("Caerleon,Bridgewatch,Fort Sterling"),
):
    """
    Cruza frequência de armas no PvP recente com spread de preço no mercado.
    """
    _validate_region(region)
    city_list = _parse_cities(cities, fallback=DEFAULT_CITY_FALLBACK)

    events = _gameinfo_get("/events", {"limit": kill_limit})
    weapon_counter: Counter[str] = Counter()

    for event in events:
        for side in ("Killer", "Victim"):
            weapon = (
                event.get(side, {})
                .get("Equipment", {})
                .get("MainHand", {})
                .get("Type")
            )
            if isinstance(weapon, str) and weapon:
                weapon_counter[weapon.upper()] += 1

    if not weapon_counter:
        return {
            "region": region,
            "cities": city_list,
            "kill_events_analyzed": kill_limit,
            "as_of": datetime.now(timezone.utc).isoformat(),
            "data": [],
        }

    top_weapon_ids = [item_id for item_id, _ in weapon_counter.most_common(top_items)]
    market_rows = get_prices(
        items=top_weapon_ids,
        locations=city_list,
        region=region,
    )

    market_by_item: Dict[str, dict] = {}
    for row in market_rows:
        item_id = row.get("item_id")
        price = row.get("sell_price_min", 0)
        if not item_id or not isinstance(price, (int, float)) or price <= 0:
            continue

        current = market_by_item.setdefault(
            item_id,
            {
                "min_price": price,
                "min_city": row.get("city"),
                "max_price": price,
                "max_city": row.get("city"),
            },
        )
        if price < current["min_price"]:
            current["min_price"] = price
            current["min_city"] = row.get("city")
        if price > current["max_price"]:
            current["max_price"] = price
            current["max_city"] = row.get("city")

    data = []
    for item_id, frequency in weapon_counter.most_common(top_items):
        market = market_by_item.get(item_id)
        if not market:
            continue

        min_price = float(market["min_price"])
        max_price = float(market["max_price"])
        spread = max_price - min_price
        spread_pct = (spread / min_price) * 100 if min_price > 0 else 0.0
        meta_market_score = round(frequency * (1 + spread_pct / 100), 3)

        data.append(
            {
                "item_id": item_id,
                "meta_frequency": frequency,
                "buy_city": market["min_city"],
                "sell_city": market["max_city"],
                "buy_price": int(min_price),
                "sell_price": int(max_price),
                "spread": int(spread),
                "spread_pct": round(spread_pct, 2),
                "meta_market_score": meta_market_score,
            }
        )

    data.sort(key=lambda row: row["meta_market_score"], reverse=True)

    return {
        "region": region,
        "cities": city_list,
        "kill_events_analyzed": kill_limit,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }


# ── Equipment Slots ────────────────────────────────────────────────────────
EQUIPMENT_SLOTS = [
    "MainHand", "OffHand", "Head", "Armor", "Shoes", "Cape", "Mount", "Food", "Potion",
]

SIGNATURE_SLOTS = ["MainHand", "Armor", "Head"]


def _extract_full_equipment(player: dict) -> Dict[str, Any]:
    """
    Extract all 9 equipment slots from a GameInfo player object.
    Returns dict mapping slot name -> { type, quality } or None.
    """
    equip = player.get("Equipment") or {}
    result: Dict[str, Any] = {}

    for slot in EQUIPMENT_SLOTS:
        item = equip.get(slot)
        if isinstance(item, dict) and item.get("Type"):
            result[slot] = {
                "type": item["Type"],
                "quality": item.get("Quality", 1),
            }
        else:
            result[slot] = None

    return result


def _build_signature(equipment: Dict[str, Any]) -> str:
    """
    Generate a build signature from the primary slots (MainHand|Armor|Head).
    Strips enchantment suffix (@N) for grouping similar builds.
    """
    parts = []
    for slot in SIGNATURE_SLOTS:
        item = equipment.get(slot)
        if item and item.get("type"):
            base_type = item["type"].split("@")[0]
            parts.append(base_type)
        else:
            parts.append("EMPTY")
    return "|".join(parts)


def _price_equipment_batch(
    equipment: Dict[str, Any], region: str, city_list: List[str]
) -> Dict[str, Any]:
    """
    Fetch prices for all equipment items in a single batch call to AODP.
    Returns equipment dict enriched with price/city data.
    """
    item_ids = []
    slot_map: Dict[str, str] = {}

    for slot, item in equipment.items():
        if item and item.get("type"):
            item_id = item["type"]
            item_ids.append(item_id)
            slot_map[item_id] = slot

    if not item_ids:
        return equipment

    # Batch fetch — AODP supports up to ~100 items in a single URL
    price_data = get_prices(
        items=list(set(item_ids)),
        locations=city_list,
        region=region,
    )

    # Index: best (cheapest) price per item_id
    best_price: Dict[str, dict] = {}
    for row in price_data:
        iid = row.get("item_id", "")
        price = row.get("sell_price_min", 0)
        if price <= 0:
            continue
        if iid not in best_price or price < best_price[iid]["price"]:
            best_price[iid] = {"price": price, "city": row.get("city", "")}

    # Enrich equipment
    priced = {}
    for slot, item in equipment.items():
        if item and item.get("type"):
            bp = best_price.get(item["type"])
            priced[slot] = {
                "type": item["type"],
                "quality": item.get("quality", 1),
                "price": bp["price"] if bp else 0,
                "city": bp["city"] if bp else "",
            }
        else:
            priced[slot] = None

    return priced


@router.get("/meta-builds")
@limiter.limit("15/minute")
def meta_builds(
    request: Request,
    region: str = Query("europe", description="europe, west ou east"),
    kill_limit: int = Query(40, ge=10, le=51),
    top_builds: int = Query(8, ge=3, le=15),
    min_ip: int = Query(0, ge=0, description="Filtro de IP mínimo do killer"),
):
    """
    Analisa builds completos dos últimos kills do PvP.
    Agrupa por assinatura (MainHand + Armor + Head), precifica cada peça,
    e retorna um ranking dos builds mais usados com custo total.
    """
    _validate_region(region)
    city_list = _parse_cities(None, fallback=DEFAULT_CITY_FALLBACK)

    events = _gameinfo_get("/events", {"limit": kill_limit})

    # Group builds by signature
    builds_map: Dict[str, dict] = {}

    for event in events:
        killer = event.get("Killer") or {}
        avg_ip = killer.get("AverageItemPower", 0)
        if min_ip and avg_ip < min_ip:
            continue

        equipment = _extract_full_equipment(killer)
        sig = _build_signature(equipment)

        # Skip builds with no weapon
        if sig.startswith("EMPTY"):
            continue

        if sig not in builds_map:
            builds_map[sig] = {
                "signature": sig,
                "frequency": 0,
                "total_ip": 0,
                "equipment_sample": equipment,
                "kills_sample": [],
            }

        builds_map[sig]["frequency"] += 1
        builds_map[sig]["total_ip"] += avg_ip

        # Keep up to 3 kill samples
        if len(builds_map[sig]["kills_sample"]) < 3:
            victim = event.get("Victim") or {}
            builds_map[sig]["kills_sample"].append({
                "killer_name": killer.get("Name", "Unknown"),
                "victim_name": victim.get("Name", "Unknown"),
                "fame": event.get("TotalVictimKillFame", 0),
                "timestamp": event.get("TimeStamp", ""),
            })

    # Sort by frequency and take top N
    sorted_builds = sorted(
        builds_map.values(),
        key=lambda b: b["frequency"],
        reverse=True,
    )[:top_builds]

    # Price the equipment for each top build
    result_builds = []
    for rank, build in enumerate(sorted_builds, 1):
        priced_equip = _price_equipment_batch(
            build["equipment_sample"], region, city_list
        )

        total_cost = sum(
            item["price"]
            for item in priced_equip.values()
            if item and item.get("price")
        )

        avg_ip = round(build["total_ip"] / build["frequency"]) if build["frequency"] else 0

        result_builds.append({
            "rank": rank,
            "frequency": build["frequency"],
            "avg_ip": avg_ip,
            "signature": build["signature"],
            "equipment": priced_equip,
            "total_cost": total_cost,
            "kills_sample": build["kills_sample"],
        })

    return {
        "region": region,
        "kill_events_analyzed": kill_limit,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "builds": result_builds,
    }


@router.get("/guild/{guild_id}/summary")
@limiter.limit("20/minute")
def guild_summary(request: Request, guild_id: str):
    """
    Lightweight guild summary — stats only, no pricing.
    Returns guild info + aggregated kill/death fame.
    """
    guild = _gameinfo_get(f"/guilds/{guild_id}")
    members = _gameinfo_get(f"/guilds/{guild_id}/members")

    total_kill_fame = sum(m.get("KillFame", 0) for m in members)
    total_death_fame = sum(m.get("DeathFame", 0) for m in members)
    total_pve_fame = sum(m.get("LifetimeStatistics", {}).get("PvE", {}).get("Total", 0) for m in members)

    top_killers = sorted(members, key=lambda m: m.get("KillFame", 0), reverse=True)[:10]
    top_deaths = sorted(members, key=lambda m: m.get("DeathFame", 0), reverse=True)[:10]

    def _member_summary(m: dict) -> dict:
        return {
            "id": m.get("Id"),
            "name": m.get("Name"),
            "kill_fame": m.get("KillFame", 0),
            "death_fame": m.get("DeathFame", 0),
            "pve_fame": m.get("LifetimeStatistics", {}).get("PvE", {}).get("Total", 0),
        }

    return {
        "guild": {
            "id": guild.get("Id"),
            "name": guild.get("Name"),
            "founder": guild.get("FounderName"),
            "alliance_id": guild.get("AllianceId"),
            "alliance_name": guild.get("AllianceTag") or guild.get("AllianceName", ""),
            "member_count": len(members),
            "kill_fame": guild.get("killFame", 0),
            "death_fame": guild.get("DeathFame", 0),
        },
        "stats": {
            "total_kill_fame": total_kill_fame,
            "total_death_fame": total_death_fame,
            "total_pve_fame": total_pve_fame,
            "fame_ratio": round(total_kill_fame / max(total_death_fame, 1), 2),
        },
        "top_killers": [_member_summary(m) for m in top_killers],
        "top_deaths": [_member_summary(m) for m in top_deaths],
    }


@router.get("/guild/{guild_id}/economy")
@limiter.limit("10/minute")
def guild_economy(
    request: Request,
    guild_id: str,
    member_limit: int = Query(15, ge=5, le=30, description="Top N membros para analisar"),
    region: str = Query("europe"),
):
    """
    Financial analysis of a guild's recent PvP activity.
    Prices equipment from kills and deaths of top members.
    """
    _validate_region(region)
    city_list = _parse_cities(None, fallback=DEFAULT_CITY_FALLBACK)
    members = _gameinfo_get(f"/guilds/{guild_id}/members")

    # Pick top members by KillFame
    top_members = sorted(members, key=lambda m: m.get("KillFame", 0), reverse=True)[:member_limit]

    member_rows = []
    all_item_ids: List[str] = []

    for member in top_members:
        mid = member.get("Id")
        if not mid:
            continue

        kills_value = 0
        deaths_value = 0
        kill_count = 0
        death_count = 0

        # Fetch recent kills for this member
        try:
            kills = _gameinfo_get(f"/players/{mid}/kills", {"limit": 10})
        except Exception:
            kills = []

        for ev in kills:
            victim = ev.get("Victim") or {}
            victim_equip = _extract_full_equipment(victim)
            # Collect item IDs for batch pricing
            for slot_item in victim_equip.values():
                if slot_item and slot_item.get("type"):
                    all_item_ids.append(slot_item["type"])
            kill_count += 1

        # Fetch recent deaths for this member
        try:
            deaths = _gameinfo_get(f"/players/{mid}/deaths", {"limit": 10})
        except Exception:
            deaths = []

        for ev in deaths:
            victim = ev.get("Victim") or {}
            victim_equip = _extract_full_equipment(victim)
            for slot_item in victim_equip.values():
                if slot_item and slot_item.get("type"):
                    all_item_ids.append(slot_item["type"])
            death_count += 1

        member_rows.append({
            "id": mid,
            "name": member.get("Name", "Unknown"),
            "kill_fame": member.get("KillFame", 0),
            "death_fame": member.get("DeathFame", 0),
            "kill_count": kill_count,
            "death_count": death_count,
            "kills_raw": kills,
            "deaths_raw": deaths,
        })

    # Batch price all unique items at once
    unique_items = list(set(all_item_ids))
    price_index: Dict[str, int] = {}

    if unique_items:
        # Chunk to stay within URL limits
        chunk_size = 80
        for i in range(0, len(unique_items), chunk_size):
            chunk = unique_items[i:i + chunk_size]
            price_rows = get_prices(items=chunk, locations=city_list, region=region)
            for row in price_rows:
                iid = row.get("item_id", "")
                price = row.get("sell_price_min", 0)
                if price > 0 and (iid not in price_index or price < price_index[iid]):
                    price_index[iid] = price

    # Calculate silver values for each member
    total_destroyed = 0
    total_lost = 0
    economy_rows = []

    for mr in member_rows:
        destroyed = 0
        lost = 0

        for kill_ev in mr.get("kills_raw", []):
            victim = kill_ev.get("Victim") or {}
            equip = victim.get("Equipment") or {}
            inv = victim.get("Inventory") or []

            for slot_name in EQUIPMENT_SLOTS:
                item = equip.get(slot_name)
                if isinstance(item, dict) and item.get("Type"):
                    destroyed += price_index.get(item["Type"], 0)

            for inv_item in inv:
                if isinstance(inv_item, dict) and inv_item.get("Type"):
                    count = inv_item.get("Count", 1)
                    destroyed += price_index.get(inv_item["Type"], 0) * count

        for death_ev in mr.get("deaths_raw", []):
            victim = death_ev.get("Victim") or {}
            equip = victim.get("Equipment") or {}
            inv = victim.get("Inventory") or []

            for slot_name in EQUIPMENT_SLOTS:
                item = equip.get(slot_name)
                if isinstance(item, dict) and item.get("Type"):
                    lost += price_index.get(item["Type"], 0)

            for inv_item in inv:
                if isinstance(inv_item, dict) and inv_item.get("Type"):
                    count = inv_item.get("Count", 1)
                    lost += price_index.get(inv_item["Type"], 0) * count

        total_destroyed += destroyed
        total_lost += lost

        economy_rows.append({
            "id": mr["id"],
            "name": mr["name"],
            "kill_fame": mr["kill_fame"],
            "death_fame": mr["death_fame"],
            "kills": mr["kill_count"],
            "deaths": mr["death_count"],
            "silver_destroyed": destroyed,
            "silver_lost": lost,
            "balance": destroyed - lost,
        })

    economy_rows.sort(key=lambda r: r["balance"], reverse=True)

    return {
        "region": region,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "totals": {
            "silver_destroyed": total_destroyed,
            "silver_lost": total_lost,
            "balance": total_destroyed - total_lost,
            "members_analyzed": len(economy_rows),
        },
        "members": economy_rows,
    }
