from __future__ import annotations

from pathlib import Path

import httpx

from core import settings
from services.cache import JsonFileCache

_cache = JsonFileCache(Path(".cache/soil"), ttl_seconds=86400 * 30)


def _extract_ph(payload: dict) -> float | None:
    layers = payload.get("properties", {}).get("layers", [])
    if not layers:
        return None

    first_layer = layers[0]
    depths = first_layer.get("depths", [])
    if not depths:
        return None

    mean_value = None
    for depth in depths:
        values = depth.get("values", {})
        candidate = values.get("mean")
        if candidate is not None:
            mean_value = candidate
            break
    if mean_value is None:
        return None

    # SoilGrids phh2o uses pH*10 convention in some layers.
    value = float(mean_value)
    return value / 10.0 if value > 14 else value


def get_soil_properties(lat: float, lon: float) -> dict[str, float | str | bool]:
    cache_key = f"soilgrids:{lat:.4f}:{lon:.4f}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    with httpx.Client(timeout=20.0) as client:
        response = client.get(
            settings.soilgrids_url,
            params={"lon": lon, "lat": lat, "property": "phh2o", "depth": "0-5cm"},
        )
        response.raise_for_status()
        data = response.json()

    ph = _extract_ph(data)
    result = {
        "ph": float(ph) if ph is not None else None,
        "texture": "unknown",
        "estimated": True,
        "source": "soilgrids",
    }
    _cache.set(cache_key, result)
    return result
