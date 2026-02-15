from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from services.rag import rag_search

DATA_PATH = Path("data") / "icar_agro_zones_india_exploded.csv"
BASE_PATH = Path("data") / "icar_agro_zones_india.csv"
EPS = 0.05
XAI_FEATURE_BOOST = 0.02
XAI_FEATURE_BOOST_MAX = 0.06

_LOCATION_ALIASES = {
    "national capital territory of delhi": "delhi",
    "nct of delhi": "delhi",
    "nct delhi": "delhi",
    "delhi division": "delhi",
    "new delhi": "delhi",
    "bombay": "mumbai",
    "bengaluru": "bangalore",
}

_CITY_TO_STATE = {
    "delhi": "delhi",
    "mumbai": "maharashtra",
    "pune": "maharashtra",
    "bangalore": "karnataka",
    "bengaluru": "karnataka",
    "chennai": "tamil nadu",
    "kolkata": "west bengal",
    "hyderabad": "telangana",
    "ahmedabad": "gujarat",
    "jaipur": "rajasthan",
}

_FEATURE_KEYWORDS = {
    "n": ["nitrogen", "npk", "nutrient"],
    "p": ["phosphorus", "npk", "nutrient"],
    "k": ["potassium", "npk", "nutrient"],
    "temperature": ["temperature", "heat", "cool", "climate"],
    "humidity": ["humidity", "moisture", "rainfall", "flood"],
    "ph": ["ph", "soil reaction", "salinity", "alkaline", "acidic"],
}


@dataclass
class ZoneMatch:
    zone_resolution: str
    zone_id: str | None
    state: str | None
    district: str | None
    matched_row: dict[str, Any] | None


@lru_cache(maxsize=1)
def _load_exploded() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Missing ICAR exploded dataset: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    for c in ["state", "district", "season", "crop", "suitability", "zone_id", "key_risks", "source_ref"]:
        df[c] = df[c].fillna("").astype(str)
    df["_state_norm"] = df["state"].map(_norm)
    df["_district_norm"] = df["district"].map(_norm)
    df["_season_norm"] = df["season"].map(_norm)
    df["_crop_norm"] = df["crop"].map(_norm)
    return df


@lru_cache(maxsize=1)
def _load_base() -> pd.DataFrame:
    if not BASE_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(BASE_PATH)
    for c in ["states", "districts", "zone_id", "zone_name", "season"]:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str)
    for c in ["lat_min", "lat_max", "lon_min", "lon_max"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "states" in df.columns:
        df["_states_norm"] = df["states"].map(_norm)
    if "season" in df.columns:
        df["_season_norm"] = df["season"].map(_norm)
    return df


def _norm(s: str | None) -> str:
    text = (s or "").strip().lower()
    text = _LOCATION_ALIASES.get(text, text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_top_shap_features(shap_sorted: list[dict[str, Any]] | None, max_features: int = 3) -> list[str]:
    if not shap_sorted:
        return []
    out: list[str] = []
    for row in shap_sorted:
        name = _norm(str(row.get("feature", "")))
        if not name:
            continue
        if name not in _FEATURE_KEYWORDS:
            continue
        if name in out:
            continue
        out.append(name)
        if len(out) >= max_features:
            break
    return out


def _candidate_tokens(region: str | None, location: str | None) -> list[str]:
    raw = [region or "", location or ""]
    parts: list[str] = []
    for item in raw:
        if not item:
            continue
        parts.append(item)
        parts.extend(x.strip() for x in item.split(",") if x.strip())
    out: list[str] = []
    seen: set[str] = set()
    for p in parts:
        n = _norm(p)
        if not n or n in seen:
            continue
        seen.add(n)
        out.append(n)
        mapped = _CITY_TO_STATE.get(n)
        if mapped:
            m = _norm(mapped)
            if m and m not in seen:
                seen.add(m)
                out.append(m)
    return out


def month_to_season(month: int | None) -> str:
    m = month or 1
    if m in (6, 7, 8, 9, 10):
        return "kharif"
    if m in (11, 12, 1, 2, 3):
        return "rabi"
    return "zaid"


def resolve_zone(location: str | None, region: str | None, lat: float | None = None, lon: float | None = None) -> ZoneMatch:
    df = _load_exploded()
    tokens = _candidate_tokens(region=region, location=location)

    for token in tokens:
        exact_d = df[df["_district_norm"] == token]
        if not exact_d.empty:
            r = exact_d.iloc[0].to_dict()
            return ZoneMatch("district", str(r.get("zone_id")), str(r.get("state")), str(r.get("district")), r)

        exact_s = df[df["_state_norm"] == token]
        if not exact_s.empty:
            r = exact_s.iloc[0].to_dict()
            return ZoneMatch("state", str(r.get("zone_id")), str(r.get("state")), str(r.get("district")), r)

    for token in tokens:
        partial_d = df[df["_district_norm"].str.contains(rf"\b{re.escape(token)}\b", regex=True)]
        if not partial_d.empty:
            r = partial_d.iloc[0].to_dict()
            return ZoneMatch("district", str(r.get("zone_id")), str(r.get("state")), str(r.get("district")), r)

        partial_s = df[df["_state_norm"].str.contains(rf"\b{re.escape(token)}\b", regex=True)]
        if not partial_s.empty:
            r = partial_s.iloc[0].to_dict()
            return ZoneMatch("state", str(r.get("zone_id")), str(r.get("state")), str(r.get("district")), r)

    if lat is not None and lon is not None:
        base = _load_base()
        if not base.empty and {"lat_min", "lat_max", "lon_min", "lon_max"}.issubset(base.columns):
            m = base[
                (base["lat_min"].notna())
                & (base["lat_max"].notna())
                & (base["lon_min"].notna())
                & (base["lon_max"].notna())
                & (base["lat_min"] <= float(lat))
                & (base["lat_max"] >= float(lat))
                & (base["lon_min"] <= float(lon))
                & (base["lon_max"] >= float(lon))
            ]
            if not m.empty:
                r = m.iloc[0].to_dict()
                st = str(r.get("states", "")).split("|")[0].strip() or None
                return ZoneMatch("latlon", str(r.get("zone_id")) if r.get("zone_id") else None, st, None, r)
        return ZoneMatch("latlon", None, None, None, None)

    return ZoneMatch("unknown", None, None, None, None)


def _token_value(text: str, key: str) -> str | None:
    m = re.search(rf"(?m)^{re.escape(key)}:([^\n]+)$", text)
    return m.group(1).strip() if m else None


def _base_from_token(suit: str | None) -> float:
    s = (suit or "").strip().upper()
    if s == "HIGH":
        return 0.85
    if s == "MED":
        return 0.65
    if s == "LOW":
        return 0.40
    return 0.50


def _match_quality(zone_resolution: str) -> float:
    return {
        "district": 1.00,
        "state": 0.92,
        "latlon": 0.90,
        "unknown": 0.75,
    }.get(zone_resolution, 0.75)


def _risk_adjust(risks: str, features: dict[str, float]) -> float:
    low = risks.lower()
    adj = 0.0
    humidity = float(features.get("humidity", 0.0))
    temperature = float(features.get("temperature", 0.0))
    ph = float(features.get("ph", 7.0))

    if "drought" in low and (humidity < 45 or temperature > 34):
        adj -= 0.05
    if "flood" in low and humidity > 85:
        adj -= 0.05
    if "salinity" in low and ph > 8.0:
        adj -= 0.05
    if "frost" in low and temperature < 10:
        adj -= 0.05
    return adj


def _is_authentic_hit(text: str) -> bool:
    source_name = (_token_value(text, "SOURCE_NAME") or "").lower()
    source_ref = (_token_value(text, "SOURCE_REF") or "").strip().lower()
    if not source_ref.startswith("http://") and not source_ref.startswith("https://"):
        return False
    if "compiled notes" in source_name or "compiled notes" in source_ref:
        return False
    return True


def _sort_hits_by_match(hits: list[dict[str, str]], state: str | None, district: str | None) -> list[dict[str, str]]:
    st = _norm(state)
    dt = _norm(district)

    def _score(h: dict[str, str]) -> tuple[int, int]:
        txt = h.get("text", "")
        hs = _norm(_token_value(txt, "STATE"))
        hd = _norm(_token_value(txt, "DISTRICT"))
        if dt and hd == dt:
            return (3, 1)
        if st and hs == st:
            return (2, 1)
        if dt and dt in hd:
            return (1, 1)
        if st and st in hs:
            return (1, 0)
        return (0, 0)

    return sorted(hits, key=_score, reverse=True)


def _season_hits_for_crop(
    hits: list[dict[str, str]],
    crop: str,
    season: str,
    state: str | None,
    district: str | None,
) -> list[dict[str, str]]:
    out = []
    c = _norm(crop)
    season_norm = _norm(season)
    for h in _sort_hits_by_match(hits, state=state, district=district):
        txt = h.get("text", "")
        h_crop = _norm(_token_value(txt, "CROP"))
        h_season = _norm(_token_value(txt, "SEASON"))
        if h_crop == c and h_season == season_norm:
            out.append(h)
    return out


def _xai_feature_matches_in_text(text: str, top_features: list[str]) -> list[str]:
    low = text.lower()
    matched: list[str] = []
    for feat in top_features:
        words = _FEATURE_KEYWORDS.get(feat, [])
        if any(w in low for w in words):
            matched.append(feat)
    return matched


def _fallback_row_for_crop(crop: str, season: str, state: str | None, district: str | None) -> dict[str, Any] | None:
    df = _load_exploded()
    c = _norm(crop)
    s = _norm(season)
    base = df[(df["_crop_norm"] == c) & (df["_season_norm"] == s)]
    if base.empty:
        return None

    dt = _norm(district)
    st = _norm(state)
    if dt:
        d = base[base["_district_norm"] == dt]
        if not d.empty:
            return d.iloc[0].to_dict()
    if st:
        m = base[base["_state_norm"] == st]
        if not m.empty:
            return m.iloc[0].to_dict()
    return base.iloc[0].to_dict()


def rerank_with_icar_rag(
    *,
    topk: list[dict[str, Any]],
    features: dict[str, float],
    shap_sorted: list[dict[str, Any]] | None = None,
    location: str | None,
    region: str | None,
    month: int | None,
    lat: float | None = None,
    lon: float | None = None,
    eps: float = EPS,
) -> dict[str, Any]:
    season = month_to_season(month)
    zone = resolve_zone(location=location, region=region, lat=lat, lon=lon)

    state = zone.state
    district = zone.district
    zone_name = district or state or _norm(region or location) or "unknown"
    top_shap_features = _extract_top_shap_features(shap_sorted, max_features=3)
    xai_query_terms = sorted({kw for f in top_shap_features for kw in _FEATURE_KEYWORDS.get(f, [])})

    all_queries: list[str] = []
    all_hits: list[dict[str, str]] = []
    scored: list[dict[str, Any]] = []
    xai_per_crop: list[dict[str, Any]] = []

    for item in topk:
        crop = str(item["crop"]).lower()
        raw = float(item["confidence"])

        q1 = f"{zone_name} {season} suitability {crop}"
        q2 = f"{crop} constraints risks {zone_name} {season}"
        q3 = f"{zone_name} dominant crops {season}"
        queries = [q1, q2, q3]
        if xai_query_terms:
            q4 = f"{zone_name} {season} {crop} {' '.join(xai_query_terms)}"
            queries.append(q4)
        all_queries.extend(queries)

        hits: list[dict[str, str]] = []
        for q in queries:
            hits.extend(rag_search(q, k=8, corpus_dir="rag_corpus/icar_zones"))

        seen = set()
        dedup_hits = []
        for h in hits:
            hid = h.get("id")
            if hid in seen:
                continue
            seen.add(hid)
            dedup_hits.append(h)

        filtered_hits = [h for h in dedup_hits if _is_authentic_hit(h.get("text", ""))]
        all_hits.extend(filtered_hits[:4])

        relevant = _season_hits_for_crop(filtered_hits, crop, season, state, district)
        xai_matches: list[str] = []

        if relevant:
            chosen = relevant[0]
            chosen_text = chosen.get("text", "")
            suit_token = _token_value(chosen_text, "SUITABILITY")
            risks = _token_value(chosen_text, "RISK") or ""
            for h in relevant[:3]:
                xai_matches.extend(_xai_feature_matches_in_text(h.get("text", ""), top_shap_features))
            xai_matches = sorted(set(xai_matches))
            explain_tokens = {
                "suitability_token": suit_token or "NOT_FOUND",
                "risk_tokens": risks,
                "source": _token_value(chosen_text, "SOURCE_REF") or "",
                "match_source": "rag_hit",
            }
        else:
            row = _fallback_row_for_crop(crop=crop, season=season, state=state, district=district)
            if row:
                suit_token = str(row.get("suitability", ""))
                risks = str(row.get("key_risks", ""))
                row_text = " ".join(
                    [
                        str(row.get("evidence_text", "")),
                        str(row.get("soil_notes", "")),
                        str(row.get("climate_notes", "")),
                        str(row.get("key_risks", "")),
                    ]
                )
                xai_matches = sorted(set(_xai_feature_matches_in_text(row_text, top_shap_features)))
                explain_tokens = {
                    "suitability_token": suit_token or "NOT_FOUND",
                    "risk_tokens": risks,
                    "source": str(row.get("source_ref", "")),
                    "match_source": "table_fallback",
                }
            else:
                suit_token = None
                risks = ""
                explain_tokens = {
                    "suitability_token": "NOT_FOUND",
                    "risk_tokens": "",
                    "source": "",
                    "match_source": "none",
                }

        base_score = _base_from_token(suit_token)
        risk_adj = _risk_adjust(risks, features)
        xai_adj = min(XAI_FEATURE_BOOST * len(xai_matches), XAI_FEATURE_BOOST_MAX)
        match_q = _match_quality(zone.zone_resolution)
        rag_suitability = float(np.clip(((base_score + risk_adj + xai_adj) * match_q), 0.0, 1.0))
        adjusted = raw * (rag_suitability + eps)
        explain_tokens["xai_feature_matches"] = xai_matches
        explain_tokens["xai_adjustment"] = float(xai_adj)

        scored.append(
            {
                "crop": crop,
                "raw_model_confidence": raw,
                "rag_suitability": rag_suitability,
                "adjusted_confidence": adjusted,
                "explanation_tokens": explain_tokens,
            }
        )
        xai_per_crop.append(
            {
                "crop": crop,
                "top_shap_features": top_shap_features,
                "matched_features": xai_matches,
                "xai_adjustment": float(xai_adj),
                "query_terms_used": xai_query_terms,
            }
        )

    scored.sort(key=lambda x: x["adjusted_confidence"], reverse=True)

    raw_top = str(topk[0]["crop"]).lower() if topk else None
    new_top = str(scored[0]["crop"]).lower() if scored else None
    conflict = None
    if raw_top and new_top and raw_top != new_top:
        raw_top_item = next((x for x in scored if x["crop"] == raw_top), None)
        new_top_item = scored[0]
        conflict = {
            "previous_top_crop": raw_top,
            "previous_raw_confidence": float(topk[0]["confidence"]),
            "previous_suitability": float(raw_top_item["rag_suitability"]) if raw_top_item else None,
            "final_crop": new_top,
            "final_adjusted_confidence": float(new_top_item["adjusted_confidence"]),
            "final_suitability": float(new_top_item["rag_suitability"]),
        }

    return {
        "season": season,
        "zone_resolution": zone.zone_resolution,
        "zone_id": zone.zone_id,
        "zone_state": state,
        "zone_district": district,
        "zone_match": zone.matched_row,
        "queries": all_queries,
        "retrieval_hits": all_hits,
        "adjusted_topk": scored,
        "rerank_conflict": conflict,
        "xai_rag_reasoning": {
            "enabled": bool(top_shap_features),
            "top_shap_features": top_shap_features,
            "query_terms": xai_query_terms,
            "per_crop": xai_per_crop,
        },
    }
