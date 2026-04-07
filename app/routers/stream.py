import asyncio
import json
import os
import random
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from time import monotonic

from fastapi import APIRouter, Query, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/stream", tags=["Live Price Stream (SSE)"])

DEFAULT_ITEMS = [
    "T4_BAG",
    "T5_CAPE",
    "T8_MAIN_AXE",
    "T8_ROYALCALF",
    "T6_CAPE",
]
DEFAULT_CITIES = ["Caerleon", "Bridgewatch", "Martlock", "Lymhurst"]


def _parse_csv_param(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [value.strip() for value in raw.split(",") if value.strip()]


async def _price_generator(
    request: Request,
    items: list[str],
    cities: list[str],
    min_interval_seconds: int,
    max_interval_seconds: int,
    session_seconds: int,
) -> AsyncGenerator[dict[str, object], None]:
    """
    Mock SSE stream that emits periodic price bumps.
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
            }
        ),
    }

    while True:
        if await request.is_disconnected():
            break

        if monotonic() - started_at >= session_seconds:
            break

        await asyncio.sleep(random.randint(min_interval_seconds, max_interval_seconds))

        if monotonic() - started_at >= session_seconds:
            break

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
):
    """
    SSE endpoint consumed by frontend EventSource.
    """
    is_vercel = os.getenv("VERCEL") == "1" or os.getenv("VERCEL") == "true"
    default_session_seconds = 8 if is_vercel else 240
    effective_session_seconds = session_seconds or default_session_seconds

    if is_vercel:
        min_interval_seconds = 2
        max_interval_seconds = 4
    else:
        min_interval_seconds = 30
        max_interval_seconds = 60

    parsed_items = _parse_csv_param(items) or DEFAULT_ITEMS
    parsed_cities = _parse_csv_param(cities) or DEFAULT_CITIES
    generator = _price_generator(
        request=request,
        items=parsed_items,
        cities=parsed_cities,
        min_interval_seconds=min_interval_seconds,
        max_interval_seconds=max_interval_seconds,
        session_seconds=effective_session_seconds,
    )
    return EventSourceResponse(generator, ping=5)
