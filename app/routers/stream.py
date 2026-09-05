import asyncio
import json
import os
import random
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from time import monotonic

from fastapi import APIRouter, Query, Request
from sse_starlette.sse import EventSourceResponse

from app.core.limiter import limiter
from app.utils.albion_client import get_prices

router = APIRouter(prefix="/stream", tags=["Live Price Stream (SSE)"])

DEFAULT_ITEMS = [
    "T4_BAG",
    "T5_CAPE",
    "T8_MAIN_AXE",
    "T8_ROYALCALF",
    "T6_CAPE",
]
DEFAULT_CITIES = ["Caerleon", "Bridgewatch", "Martlock", "Lymhurst", "Fort Sterling"]

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


def _normalize_city_name(raw_city: str) -> str:
    city = (raw_city or "").strip()
    if not city:
        return ""
    key = city.lower().replace("_", " ").replace("-", " ")
    key = " ".join(key.split())
    return CITY_ALIASES.get(key, city)


def _parse_csv_param(raw: str | None, *, city: bool = False) -> list[str]:
    if not raw:
        return []
    values = [value.strip() for value in raw.split(",") if value.strip()]
    if not city:
        return values
    return [_normalize_city_name(value) for value in values]


async def _price_generator(
    request: Request,
    items: list[str],
    cities: list[str],
    interval_seconds: int,
    session_seconds: int,
    region: str,
    mode: str,
) -> AsyncGenerator[dict[str, object], None]:
    """
    SSE de preços com modo real (Albion Data API) e fallback mock.
    For serverless environments, we keep short-lived sessions and let EventSource reconnect.
    """
    started_at = monotonic()
    state: dict[tuple[str, str], int] = {}

    # Initial event so clients know the channel is alive.
    yield {
        "event": "price_update",
        "retry": 2000,
        "data": json.dumps(
            {
                "type": "CONNECTED",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "mode": mode,
                "region": region,
            }
        ),
    }

    while True:
        if await request.is_disconnected():
            break

        if monotonic() - started_at >= session_seconds:
            break

        await asyncio.sleep(interval_seconds)

        if monotonic() - started_at >= session_seconds:
            break

        sent_realtime = False
        allow_realtime = mode in {"auto", "real"}
        allow_mock_fallback = mode in {"auto", "mock"}

        if allow_realtime:
            try:
                market_rows = get_prices(
                    items=items,
                    locations=cities,
                    region=region,
                )
                for row in market_rows:
                    item_name = row.get("item_id")
                    city = row.get("city")
                    price = row.get("sell_price_min", 0)
                    if not item_name or not city:
                        continue
                    if not isinstance(price, (int, float)) or price <= 0:
                        continue

                    key = (str(item_name), str(city))
                    previous = state.get(key)
                    next_price = int(price)
                    state[key] = next_price

                    # Só emite quando há valor inicial ou mudança real.
                    if previous is not None and previous == next_price:
                        continue

                    variation_pct = 0.0
                    if previous and previous > 0:
                        variation_pct = round(((next_price - previous) / previous) * 100, 2)

                    payload = {
                        "item_name": key[0],
                        "city": key[1],
                        "old_price": previous if previous is not None else next_price,
                        "new_price": next_price,
                        "variation_pct": variation_pct,
                        "type": "SNAPSHOT" if previous is None else "REAL_UPDATE",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                    sent_realtime = True

                    yield {
                        "id": f"{key[0]}:{key[1]}:{int(datetime.now(timezone.utc).timestamp())}",
                        "event": "price_update",
                        "data": json.dumps(payload),
                    }
            except Exception:
                sent_realtime = False

        if not sent_realtime and allow_mock_fallback:
            item = random.choice(items)
            city = random.choice(cities)
            key = (item, city)

            previous = state.get(key, random.randint(3_000, 180_000))
            variation = random.uniform(-0.05, 0.05)
            next_price = max(1, int(previous * (1 + variation)))
            state[key] = next_price

            payload = {
                "item_name": item,
                "city": city,
                "old_price": previous,
                "new_price": next_price,
                "variation_pct": round(((next_price - previous) / previous) * 100, 2),
                "type": "MOCK_BUMP",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            yield {
                "id": f"{item}:{city}:{int(datetime.now(timezone.utc).timestamp())}",
                "event": "price_update",
                "data": json.dumps(payload),
            }


@router.get("/prices")
@limiter.limit("20/minute")
async def stream_prices(
    request: Request,
    items: str | None = Query(
        default=None,
        description="CSV optional filter, ex: T4_BAG,T5_CAPE",
    ),
    cities: str | None = Query(
        default=None,
        description="CSV optional filter, ex: Caerleon,Bridgewatch",
    ),
    session_seconds: int | None = Query(
        default=None,
        ge=3,
        le=300,
        description="Optional maximum stream session duration before graceful close",
    ),
    region: str = Query(
        "europe",
        description="Região de mercado (europe, west, east)",
    ),
    mode: str = Query(
        "auto",
        description="auto (real+fallback), real (somente real), mock (somente mock)",
    ),
):
    """
    SSE endpoint consumed by frontend EventSource.
    """
    is_vercel = os.getenv("VERCEL") == "1" or os.getenv("VERCEL") == "true"
    default_session_seconds = 8 if is_vercel else 240
    effective_session_seconds = session_seconds or default_session_seconds

    mode_norm = (mode or "auto").lower()
    if mode_norm not in {"auto", "real", "mock"}:
        mode_norm = "auto"

    if is_vercel:
        interval_seconds = 3
    else:
        interval_seconds = 20

    parsed_items = _parse_csv_param(items) or DEFAULT_ITEMS
    parsed_cities = _parse_csv_param(cities, city=True) or DEFAULT_CITIES
    generator = _price_generator(
        request=request,
        items=parsed_items,
        cities=parsed_cities,
        interval_seconds=interval_seconds,
        session_seconds=effective_session_seconds,
        region=region,
        mode=mode_norm,
    )
    return EventSourceResponse(generator, ping=5)
