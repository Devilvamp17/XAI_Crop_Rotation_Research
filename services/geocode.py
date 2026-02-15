from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

import httpx

from core import settings
from services.cache import JsonFileCache

_cache = JsonFileCache(Path(".cache/geocode"), ttl_seconds=86400 * 30)
_rate_lock = threading.Lock()
_last_request_time = 0.0


def _respect_rate_limit() -> None:
    global _last_request_time
    with _rate_lock:
        now = time.time()
        elapsed = now - _last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        _last_request_time = time.time()


def geocode_location(location: str) -> dict[str, Any]:
    cache_key = f"nominatim:{location.strip().lower()}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    _respect_rate_limit()

    with httpx.Client(timeout=15.0, headers={"User-Agent": settings.nominatim_user_agent}) as client:
        response = client.get(
            settings.nominatim_url,
            params={"q": location, "format": "json", "limit": 1, "addressdetails": 1},
        )
        response.raise_for_status()
        data = response.json()

    if not data:
        raise ValueError(f"No geocoding result for location: {location}")

    item = data[0]
    address = item.get("address", {})
    result = {
        "query": location,
        "lat": float(item["lat"]),
        "lon": float(item["lon"]),
        "display_name": item.get("display_name", location),
        "region": address.get("state") or address.get("country") or "global",
        "country": address.get("country"),
        "source": "nominatim",
    }
    _cache.set(cache_key, result)
    return result
