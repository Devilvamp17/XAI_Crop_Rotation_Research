from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

import api.main as agent_main


def infer_tools_used(response_json: dict[str, Any]) -> list[str]:
    explicit = response_json.get("recommendation", {}).get("tool_calls")
    if isinstance(explicit, list):
        return sorted(str(x) for x in explicit)

    tools: set[str] = set()
    rec = response_json.get("recommendation", {})
    prov = rec.get("provenance", {})

    for _, meta in prov.items():
        source = str(meta.get("source", ""))
        if source == "weather_api":
            tools.add("get_weather")
        if source in {"soil_api", "soil_api_fallback"}:
            tools.add("get_soil_properties")

    if rec.get("calendar_adjustment"):
        tools.add("get_crop_calendar")

    if any(
        str(v.get("source", "")).endswith("api") or str(v.get("source", "")).endswith("fallback")
        for v in prov.values()
    ):
        tools.add("geocode_location")

    return sorted(tools)


def main() -> None:
    suite = json.loads(Path("prompts/llm_tool_routing_suite.json").read_text(encoding="utf-8"))
    failures: list[str] = []

    original_predict = agent_main.model_client.predict
    original_geocode = agent_main.geocode_location
    original_weather = agent_main.get_weather
    original_soil = agent_main.get_soil_properties
    original_calendar = agent_main.get_crop_calendar
    original_chat = agent_main.llm_client.chat
    client = TestClient(agent_main.app)

    try:
        agent_main.model_client.predict = lambda features, models, top_k: {
            "input": dict(features),
            "models": {
                "xgboost": {
                    "model": "xgboost",
                    "prediction": {"crop": "rice", "predicted_class": 0, "confidence": 0.80},
                    "top3": [
                        {"rank": 1, "crop": "rice", "confidence": 0.80},
                        {"rank": 2, "crop": "maize", "confidence": 0.15},
                        {"rank": 3, "crop": "wheat", "confidence": 0.05},
                    ][:top_k],
                    "shap": {"base_value": 0.0, "values": {}, "sorted_by_abs": []},
                    "lime": {"class_index": 0, "explanations": []},
                    "curves": {"topk_confidence": {"x": ["rice", "maize", "wheat"], "y": [0.80, 0.15, 0.05]}},
                }
            },
        }
        agent_main.geocode_location = lambda location: {"lat": 28.61, "lon": 77.20, "region": "global", "source": "nominatim"}
        agent_main.get_weather = lambda lat, lon: {"temperature": 30.0, "humidity": 65.0, "rainfall": 0.2}
        agent_main.get_soil_properties = lambda lat, lon: {"ph": 6.7, "texture": "unknown"}
        agent_main.get_crop_calendar = lambda region, month: {"rice": 0.1, "maize": 0.9, "wheat": 0.8}
        agent_main.llm_client.chat = lambda system_prompt, user_prompt: (
            "1) Final recommended crop + short reason\n"
            "Maize after calendar rerank.\n\n"
            "2) Confidence interpretation\n"
            "Raw model confidence (from ML): 0.8000\n"
            "Season-adjusted confidence: 0.1425 (after crop calendar). Threshold reference: 0.60\n\n"
            "3) Top-3 tradeoff note (if available)\n"
            "maize (raw=0.1500, suit=0.90, adj=0.1425).\n\n"
            "4) Action checklist\n"
            "- Check N/P/K.\n"
            "- Validate local weather.\n"
            "- Start a pilot plot.\n\n"
            "5) Risk warning\n"
            "Low-confidence recommendation."
        )

        for case in suite:
            payload = {
                "query": case["query"],
                "recommendation_input": case["recommendation_input"],
            }
            expected = case.get("expected", {})
            expected_status = int(expected.get("status", 200))

            r = client.post("/recommend_with_llm", json=payload)
            if r.status_code != expected_status:
                failures.append(
                    f"{case['id']}: expected status {expected_status}, got {r.status_code}, body={r.text[:240]}"
                )
                continue

            if r.status_code != 200:
                continue

            data = r.json()
            tools = infer_tools_used(data)
            must_include = set(expected.get("must_include_tools", []))
            must_exclude = set(expected.get("must_exclude_tools", []))

            missing = must_include.difference(tools)
            bad = must_exclude.intersection(tools)
            if missing:
                failures.append(f"{case['id']}: missing expected tools {sorted(missing)} | used={tools}")
            if bad:
                failures.append(f"{case['id']}: unexpected tools {sorted(bad)} | used={tools}")
    finally:
        agent_main.model_client.predict = original_predict
        agent_main.geocode_location = original_geocode
        agent_main.get_weather = original_weather
        agent_main.get_soil_properties = original_soil
        agent_main.get_crop_calendar = original_calendar
        agent_main.llm_client.chat = original_chat

    if failures:
        print("=== TOOL ROUTING TEST FAILURES ===")
        for f in failures:
            print("-", f)
        raise SystemExit(1)

    print("Tool routing suite passed.")


if __name__ == "__main__":
    main()
