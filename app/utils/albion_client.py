# app/utils/albion_client.py
import requests
import cachetools
from typing import List, Dict, Optional, Literal
from datetime import datetime
from app.core.config import settings

# Session com retry e compressão
session = requests.Session()
session.headers.update(
    {
        "Accept-Encoding": "gzip",
        "User-Agent": "AlbionMarketAPI/1.0",
    }
)

# Cache global para preços — TTL de 2 min para dados mais frescos
prices_cache = cachetools.TTLCache(maxsize=1000, ttl=120)  # 2 minutos

# Cache separado para histórico
history_cache = cachetools.TTLCache(maxsize=500, ttl=600)  # 10 minutos

PriceMode = Literal["sell", "buy", "any"]


def get_prices(
    items: List[str],
    locations: Optional[List[str]] = None,
    qualities: Optional[List[int]] = None,
    region: str = settings.ALBION_REGION,
    *,
    mode: PriceMode = "sell",
) -> List[Dict]:
    """
    Wrapper para o endpoint /stats/prices da Albion Data API.

    mode:
      - "sell" (default): keep rows with sell_price_min > 0 (legacy behavior)
      - "buy": keep rows with buy_price_max > 0 (needed for Black Market flips)
      - "any": keep rows with sell_price_min > 0 OR buy_price_max > 0
    """
    locations = locations or settings.DEFAULT_CITIES

    base_url = settings.ALBION_BASE_URLS.get(
        region, settings.ALBION_BASE_URLS["europe"]
    )
    # Ex.: https://europe.albion-online-data.com/api/v2/stats/prices
    url = f"{base_url}/{','.join(items)}"

    params = {
        "locations": ",".join(locations),
        "qualities": ",".join(map(str, qualities or [])) or None,
    }
    params = {k: v for k, v in params.items() if v}

    cache_key = (
        f"prices:{mode}:{region}:{','.join(items)}:"
        f"{params.get('locations')}:{params.get('qualities')}"
    )
    if cache_key in prices_cache:
        return prices_cache[cache_key]

    try:
        resp = session.get(url, params=params, timeout=settings.ALBION_API_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        valid: List[Dict] = []
        for d in data:
            sell_min = d.get("sell_price_min", 0) or 0
            buy_max = d.get("buy_price_max", 0) or 0
            if mode == "sell" and sell_min <= 0:
                continue
            if mode == "buy" and buy_max <= 0:
                continue
            if mode == "any" and sell_min <= 0 and buy_max <= 0:
                continue
            valid.append(d)

        prices_cache[cache_key] = valid
        return valid
    except Exception as e:
        print(f"[Albion] Erro prices: {e}")
        return []


def get_price_history(
    item_id: str,
    locations: Optional[List[str]] = None,
    days: int = 7,
    time_resolution: str = "6h",
    region: str = settings.ALBION_REGION,
) -> List[Dict]:
    """
    Wrapper para o endpoint /stats/history da Albion Data API.
    """
    locations = locations or settings.DEFAULT_CITIES

    cache_key = f"history:{item_id}:{','.join(locations)}:{days}:{time_resolution}:{region}"
    if cache_key in history_cache:
        return history_cache[cache_key]

    base_prices_url = settings.ALBION_BASE_URLS.get(
        region, settings.ALBION_BASE_URLS["europe"]
    )
    history_base = base_prices_url.replace("/prices", "/history")
    url = f"{history_base}/{item_id}.json"

    scale_map = {"1h": 1, "6h": 6, "24h": 24}
    time_scale = scale_map.get(time_resolution, 6)

    params = {
        "locations": ",".join(locations),
        "time-scale": time_scale,
    }

    try:
        resp = session.get(url, params=params, timeout=settings.ALBION_API_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        formatted: List[Dict] = []

        for item in data:
            city = item.get("location")
            series = item.get("data", [])
            for point in series:
                ts_raw = point.get("timestamp")
                try:
                    ts_int = int(ts_raw)
                except (TypeError, ValueError):
                    try:
                        dt = datetime.fromisoformat(str(ts_raw))
                        ts_int = int(dt.timestamp() * 1000)
                    except Exception:
                        continue

                avg_price = float(point.get("avg_price", 0) or 0)
                item_count = int(point.get("item_count", 0) or 0)

                if avg_price == 0 and item_count == 0:
                    continue

                formatted.append(
                    {
                        "timestamp": ts_int,
                        "date": datetime.fromtimestamp(ts_int / 1000).isoformat(),
                        "city": city,
                        "avg_price": avg_price,
                        "item_count": item_count,
                    }
                )

        formatted.sort(key=lambda x: x["timestamp"])
        history_cache[cache_key] = formatted
        return formatted
    except Exception as e:
        print(f"[Albion] Erro history: {e}")
        return []


def get_gold_prices(
    count: int = 1,
    region: str = settings.ALBION_REGION,
) -> List[Dict]:
    """
    Wrapper para o endpoint /stats/gold.json da Albion Data API.
    """
    base_prices_url = settings.ALBION_BASE_URLS.get(
        region, settings.ALBION_BASE_URLS["europe"]
    )
    gold_url = base_prices_url.replace("/prices", "/gold.json")

    params = {"count": count}
    cache_key = f"gold:{count}:{region}"

    if cache_key in prices_cache:
        return prices_cache[cache_key]

    try:
        resp = session.get(gold_url, params=params, timeout=settings.ALBION_API_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        prices_cache[cache_key] = data
        return data
    except Exception as e:
        print(f"[Albion] Erro gold: {e}")
        return []
