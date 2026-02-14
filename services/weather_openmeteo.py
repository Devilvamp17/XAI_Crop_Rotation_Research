from __future__ import annotations

from pathlib import Path

import httpx

from core import settings
from services.cache import JsonFileCache

_cache = JsonFileCache(Path(".cache/weather"), ttl_seconds=3600)


def get_weather(lat: float, lon: float) -> dict[str, float | str | bool]:
    cache_key = f"openmeteo:{lat:.4f}:{lon:.4f}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation",
    }

    with httpx.Client(timeout=15.0) as client:
        response = client.get(settings.open_meteo_url, params=params)
        response.raise_for_status()
        data = response.json()

    current = data.get("current", {})
    result = {
        "temperature": float(current.get("temperature_2m")),
        "humidity": float(current.get("relative_humidity_2m")),
        "rainfall": float(current.get("precipitation", 0.0)),
        "estimated": True,
        "source": "open_meteo",
    }
    _cache.set(cache_key, result)
    return result
