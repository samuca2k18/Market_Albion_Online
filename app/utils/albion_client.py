# app/utils/albion_client.py
import requests
import cachetools
from typing import List, Dict, Optional
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

# Cache global para preços
prices_cache = cachetools.TTLCache(maxsize=1000, ttl=300)  # 5 minutos

# Cache separado para histórico
history_cache = cachetools.TTLCache(maxsize=500, ttl=600)  # 10 minutos


def get_prices(
    items: List[str],
    locations: Optional[List[str]] = None,
    qualities: Optional[List[int]] = None,
    region: str = settings.ALBION_REGION,
) -> List[Dict]:
    """
    Wrapper para o endpoint /stats/prices da Albion Data API.
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

    cache_key = f"prices:{','.join(items)}:{params.get('locations')}:{params.get('qualities')}"
    if cache_key in prices_cache:
        return prices_cache[cache_key]

    try:
        resp = session.get(url, params=params, timeout=settings.ALBION_API_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        # filtra só entradas com preço mínimo > 0
        valid = [d for d in data if d.get("sell_price_min", 0) > 0]
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

    A API oficial usa:
      /api/v2/stats/history/{ITEM}.json?locations=...&time-scale=24

    O retorno é uma lista de objetos:
    [
      {
        "location": "Caerleon",
        "item_id": "T4_BAG",
        "quality": 1,
        "data": [
          {
            "timestamp": 1730150400000,
            "item_count": 123,
            "avg_price": 4567
          },
          ...
        ]
      },
      ...
    ]
    """
    locations = locations or settings.DEFAULT_CITIES

    # monta uma chave de cache manual (tudo string)
    cache_key = f"history:{item_id}:{','.join(locations)}:{days}:{time_resolution}:{region}"
    if cache_key in history_cache:
        return history_cache[cache_key]

    base_prices_url = settings.ALBION_BASE_URLS.get(
        region, settings.ALBION_BASE_URLS["europe"]
    )
    # troca "/prices" por "/history" e adiciona .json
    history_base = base_prices_url.replace("/prices", "/history")
    url = f"{history_base}/{item_id}.json"

    # Albion Data API usa "time-scale" em horas: 1, 6, 24
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

        # data = lista de cidades; cada uma tem "data": [pontos]
        for item in data:
            city = item.get("location")
            series = item.get("data", [])
            for point in series:
                ts_raw = point.get("timestamp")
                # timestamp vem em milissegundos (int ou string)
                try:
                    ts_int = int(ts_raw)
                except (TypeError, ValueError):
                    # fallback se vier em string de data
                    try:
                        dt = datetime.fromisoformat(str(ts_raw))
                        ts_int = int(dt.timestamp() * 1000)
                    except Exception:
                        continue

                avg_price = float(point.get("avg_price", 0) or 0)
                item_count = int(point.get("item_count", 0) or 0)

                # se absolutamente não tem nada, pula
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

        # guarda no cache
        history_cache[cache_key] = formatted
        return formatted
    except Exception as e:
        print(f"[Albion] Erro history: {e}")
        return []
