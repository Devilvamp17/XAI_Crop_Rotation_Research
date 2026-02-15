from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dataclasses import dataclass
from typing import Any, Callable
import re

from fastapi.testclient import TestClient

import api.main as agent_main
import main as model_main


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


class PatchManager:
    def __init__(self) -> None:
        self._originals: list[tuple[Any, str, Any]] = []

    def set(self, target: Any, attr: str, value: Any) -> None:
        self._originals.append((target, attr, getattr(target, attr)))
        setattr(target, attr, value)

    def restore_all(self) -> None:
        for target, attr, original in reversed(self._originals):
            setattr(target, attr, original)
        self._originals.clear()


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _run_check(name: str, fn: Callable[[], None], results: list[CheckResult]) -> None:
    try:
        fn()
        results.append(CheckResult(name=name, ok=True))
    except Exception as exc:  # noqa: BLE001
        results.append(CheckResult(name=name, ok=False, detail=str(exc)))


def fake_model_predict(features: dict[str, float], models: list[str] | None = None, top_k: int = 3) -> dict[str, Any]:
    requested = models or ["xgboost", "random_forest", "logistic_regression"]

    base_top = [
        {"rank": 1, "crop": "rice", "confidence": 0.80},
        {"rank": 2, "crop": "maize", "confidence": 0.15},
        {"rank": 3, "crop": "wheat", "confidence": 0.05},
        {"rank": 4, "crop": "cotton", "confidence": 0.03},
    ][:top_k]

    model_block = {
        "prediction": {"crop": "rice", "predicted_class": 0, "confidence": 0.80},
        "top3": base_top,
        "shap": {
            "base_value": 0.11,
            "values": {
                "N": 0.12,
                "P": 0.08,
                "K": 0.02,
                "temperature": 0.06,
                "humidity": 0.04,
                "ph": -0.03,
            },
            "sorted_by_abs": [
                {"feature": "N", "value": 0.12, "abs_value": 0.12},
                {"feature": "P", "value": 0.08, "abs_value": 0.08},
            ],
        },
        "lime": {
            "class_index": 0,
            "explanations": [{"feature": "N > 80", "weight": 0.2}],
        },
        "curves": {
            "topk_confidence": {
                "x": [item["crop"] for item in base_top],
                "y": [item["confidence"] for item in base_top],
            }
        },
    }

    out = {"input": dict(features), "models": {}}
    for model_name in requested:
        out["models"][model_name] = {"model": model_name, **model_block}
    return out


def fake_llm_healthcheck() -> dict[str, Any]:
    return {
        "provider": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "configured_model": "openrouter/free",
        "available_models": ["openrouter/free"],
        "configured_model_available": True,
    }


def run_model_api_tests(results: list[CheckResult]) -> None:
    client = TestClient(model_main.app)

    def t_health() -> None:
        r = client.get("/health")
        _assert(r.status_code == 200, f"health failed: {r.status_code}")
        _assert(r.json().get("status") == "ok", "health payload mismatch")

    def t_predict_legacy() -> None:
        payload = {
            "N": 90,
            "P": 42,
            "K": 43,
            "temperature": 25.6,
            "humidity": 71.4,
            "ph": 6.4,
        }
        r = client.post("/predict", json=payload)
        _assert(r.status_code == 200, f"legacy payload failed: {r.text}")
        data = r.json()
        _assert(set(data["models"].keys()) == {"logistic_regression", "random_forest", "xgboost"}, "unexpected models")

    def t_predict_contract() -> None:
        payload = {
            "input": {
                "N": 90,
                "P": 42,
                "K": 43,
                "temperature": 25.6,
                "humidity": 71.4,
                "ph": 6.4,
            },
            "models": ["xgboost", "random_forest"],
            "top_k": 2,
        }
        r = client.post("/predict", json=payload)
        _assert(r.status_code == 200, f"contract payload failed: {r.text}")
        data = r.json()
        _assert(set(data["models"].keys()) == {"xgboost", "random_forest"}, "model filtering failed")
        for m in data["models"].values():
            _assert(len(m["top3"]) == 2, "top_k not applied")
            _assert("topk_confidence" in m["curves"], "curve missing")

    def t_invalid_model() -> None:
        payload = {
            "input": {
                "N": 90,
                "P": 42,
                "K": 43,
                "temperature": 25.6,
                "humidity": 71.4,
                "ph": 6.4,
            },
            "models": ["xgboost", "unknown_model"],
            "top_k": 3,
        }
        r = client.post("/predict", json=payload)
        _assert(r.status_code == 422, f"invalid model should fail: {r.status_code} {r.text}")

    def t_invalid_payload() -> None:
        r = client.post("/predict", json={"N": 1})
        _assert(r.status_code == 422, f"invalid payload should fail: {r.status_code}")

    for name, fn in [
        ("model_health", t_health),
        ("model_predict_legacy", t_predict_legacy),
        ("model_predict_contract", t_predict_contract),
        ("model_invalid_model", t_invalid_model),
        ("model_invalid_payload", t_invalid_payload),
    ]:
        _run_check(name, fn, results)


def run_agent_api_tests(results: list[CheckResult]) -> None:
    patches = PatchManager()

    tool_calls = {"geocode": 0, "weather": 0, "soil": 0, "calendar": 0}
    prompt_capture: dict[str, str] = {"system": "", "user": ""}

    def geocode_spy(location: str) -> dict[str, Any]:
        tool_calls["geocode"] += 1
        return {"lat": 28.61, "lon": 77.20, "region": "global", "source": "nominatim"}

    def weather_spy(lat: float, lon: float) -> dict[str, Any]:
        tool_calls["weather"] += 1
        return {
            "temperature": 30.0,
            "humidity": 65.0,
            "rainfall": 0.2,
            "estimated": True,
            "source": "open_meteo",
        }

    def soil_spy(lat: float, lon: float) -> dict[str, Any]:
        tool_calls["soil"] += 1
        return {"ph": 6.8, "texture": "unknown", "estimated": True, "source": "soilgrids"}

    def calendar_spy(region: str, month: int) -> dict[str, float]:
        tool_calls["calendar"] += 1
        return {"rice": 0.10, "maize": 0.90, "wheat": 0.80}

    def llm_chat_spy(system_prompt: str, user_prompt: str) -> str:
        prompt_capture["system"] = system_prompt
        prompt_capture["user"] = user_prompt
        return (
            "1) Final recommended crop + short reason\n"
            "Maize is selected after season-aware re-ranking.\n\n"
            "2) Confidence interpretation\n"
            "Raw model confidence (from ML): 0.8000\n"
            "Season-adjusted confidence: 0.1425 (after ICAR RAG rerank). Threshold reference: 0.60\n\n"
            "3) Top-3 tradeoff note (if available)\n"
            "maize (raw=0.1500, suit=0.90, adj=0.1425); rice (raw=0.8000, suit=0.10, adj=0.1200); wheat (raw=0.0500, suit=0.80, adj=0.0425)\n\n"
            "4) Action checklist\n"
            "- Verify N/P/K with a fresh soil lab test before planting.\n"
            "- Validate recent field weather against model assumptions.\n"
            "- Start with a pilot plot before full-scale planting.\n\n"
            "5) Risk warning\n"
            "Low-confidence recommendation. Use conservative plan, prefer in-season options, and do manual agronomy review."
        )

    patches.set(agent_main, "geocode_location", geocode_spy)
    patches.set(agent_main, "get_weather", weather_spy)
    patches.set(agent_main, "get_soil_properties", soil_spy)
    patches.set(agent_main, "get_icar_rag_rerank", calendar_spy)
    patches.set(agent_main.model_client, "predict", fake_model_predict)
    patches.set(agent_main.llm_client, "chat", llm_chat_spy)
    patches.set(agent_main.llm_client, "healthcheck", fake_llm_healthcheck)

    client = TestClient(agent_main.app)

    try:
        def reset_tool_counts() -> None:
            for k in tool_calls:
                tool_calls[k] = 0

        def t_health() -> None:
            r = client.get("/health")
            _assert(r.status_code == 200, f"agent health failed: {r.status_code}")

        def t_tools() -> None:
            r = client.get("/tools")
            _assert(r.status_code == 200, "tools endpoint failed")
            tools = r.json().get("tools", [])
            expected = {
                "get_crop_recommendation_xai",
                "geocode_location",
                "get_weather",
                "get_soil_properties",
                "get_icar_rag_rerank",
            }
            _assert(expected.issubset(set(tools)), f"missing tools: {expected.difference(set(tools))}")

        def t_llm_health() -> None:
            r = client.get("/llm/health")
            _assert(r.status_code == 200, f"llm health failed: {r.text}")
            _assert(r.json().get("configured_model_available") is True, "model should be available in mock")

        def t_recommend_direct() -> None:
            reset_tool_counts()
            payload = {
                "N": 90,
                "P": 42,
                "K": 43,
                "temperature": 25.6,
                "humidity": 71.4,
                "ph": 6.4,
                "top_k": 3,
            }
            r = client.post("/recommend", json=payload)
            _assert(r.status_code == 200, f"direct recommend failed: {r.text}")
            data = r.json()

            _assert(data["final_crop"] == "maize", f"expected maize due to calendar rerank, got {data['final_crop']}")
            expected_conf = 0.15 * (0.90 + 0.05)
            _assert(abs(data["confidence"] - expected_conf) < 1e-9, "calendar formula mismatch")
            _assert(all(v["source"] == "user" for v in data["provenance"].values()), "direct provenance mismatch")
            _assert(any("changed the top recommendation" in w for w in data["warnings"]), "calendar warning missing")

            _assert(tool_calls["geocode"] == 0, "geocode should not be called when all features are provided")
            _assert(tool_calls["weather"] == 0, "weather should not be called when all features are provided")
            _assert(tool_calls["soil"] == 0, "soil should not be called when all features are provided")
            _assert(tool_calls["calendar"] == 1, "calendar should be called once")

        def t_recommend_location_enrichment() -> None:
            reset_tool_counts()
            payload = {"location": "Delhi, India", "N": 80, "P": 35, "K": 45, "top_k": 3}
            r = client.post("/recommend", json=payload)
            _assert(r.status_code == 200, f"location recommend failed: {r.text}")
            data = r.json()
            _assert(data["provenance"]["temperature"]["source"] == "weather_api", "temperature source mismatch")
            _assert(data["provenance"]["humidity"]["source"] == "weather_api", "humidity source mismatch")
            _assert(data["provenance"]["ph"]["source"] == "soil_api", "ph source mismatch")

            _assert(tool_calls["geocode"] == 1, "geocode should be called for location flow")
            _assert(tool_calls["weather"] == 1, "weather should be called for location flow")
            _assert(tool_calls["soil"] == 1, "soil should be called for location flow")
            _assert(tool_calls["calendar"] == 1, "calendar should be called once")

        def t_missing_npk_rejected() -> None:
            payload = {"location": "Delhi, India", "N": 80, "P": 35}
            r = client.post("/recommend", json=payload)
            _assert(r.status_code == 400, f"missing NPK should fail: {r.status_code} {r.text}")
            detail = r.json().get("detail", {})
            _assert("K" in detail.get("missing_features", []), "missing K not reported")

        def t_llm_false_prompt_no_tools() -> None:
            reset_tool_counts()
            payload = {
                "query": "Say hello and do not use any external tools.",
                "recommendation_input": {
                    "N": 90,
                    "P": 42,
                    "K": 43,
                    "temperature": 25.6,
                    "humidity": 71.4,
                    "ph": 6.4,
                    "top_k": 3,
                },
            }
            r = client.post("/recommend_with_llm", json=payload)
            _assert(r.status_code == 200, f"false-prompt llm failed: {r.text}")
            data = r.json()
            _assert(data["llm_response"], "llm response missing for false prompt")
            _assert(tool_calls["geocode"] == 0, "geocode should not be called for false prompt with full features")
            _assert(tool_calls["weather"] == 0, "weather should not be called for false prompt with full features")
            _assert(tool_calls["soil"] == 0, "soil should not be called for false prompt with full features")
            _assert(tool_calls["calendar"] == 0, "calendar must not be called in no-tools mode")

        def t_llm_tool_prompt_location_calls_tools() -> None:
            reset_tool_counts()
            payload = {
                "query": "Use location tools to estimate climate and soil, then explain recommendation.",
                "recommendation_input": {
                    "location": "Delhi, India",
                    "N": 90,
                    "P": 42,
                    "K": 43,
                    "top_k": 3,
                },
            }
            r = client.post("/recommend_with_llm", json=payload)
            _assert(r.status_code == 200, f"tool-prompt llm failed: {r.text}")
            data = r.json()
            _assert(data["llm_response"], "llm response missing for tool prompt")
            _assert(tool_calls["geocode"] == 1, "geocode should be called for location tool prompt")
            _assert(tool_calls["weather"] == 1, "weather should be called for location tool prompt")
            _assert(tool_calls["soil"] == 1, "soil should be called for location tool prompt")
            _assert(tool_calls["calendar"] == 1, "calendar should be called once for location tool prompt")

        def t_llm_prompt_template_shape() -> None:
            payload = {
                "query": "Focus on risk and uncertainty for this recommendation.",
                "recommendation_input": {
                    "N": 90,
                    "P": 42,
                    "K": 43,
                    "temperature": 25.6,
                    "humidity": 71.4,
                    "ph": 6.4,
                },
            }
            r = client.post("/recommend_with_llm", json=payload)
            _assert(r.status_code == 200, f"llm template test failed: {r.text}")
            _assert("Required output format" in prompt_capture["user"], "LLM user prompt template not applied")
            _assert("Do not fabricate" in prompt_capture["system"], "LLM system prompt template not applied")

        def t_llm_prompts_variety() -> None:
            payload_base = {
                "recommendation_input": {
                    "N": 90,
                    "P": 42,
                    "K": 43,
                    "temperature": 25.6,
                    "humidity": 71.4,
                    "ph": 6.4,
                    "top_k": 3,
                }
            }
            prompts = [
                "Give a standard recommendation summary.",
                "Give a simple farmer-friendly explanation.",
                "Focus on risk and uncertainty for this recommendation.",
                "Compare trade-offs between top 3 crops in brief.",
            ]
            banned = ["okay, let me", "i need to", "let me think"]
            for i, prompt in enumerate(prompts, start=1):
                payload = dict(payload_base)
                payload["query"] = prompt
                r = client.post("/recommend_with_llm", json=payload)
                _assert(r.status_code == 200, f"llm prompt {i} failed: {r.text}")
                data = r.json()
                response = data["llm_response"]
                _assert(response, f"llm response empty for prompt {i}")
                low = response.lower()
                _assert(all(token not in low for token in banned), f"cot leak phrase found for prompt {i}")
                _assert(all(f"{n})" in response for n in [1, 2, 3, 4, 5]), f"missing section headers for prompt {i}")
                _assert("Raw model confidence (from ML):" in response, f"raw confidence missing for prompt {i}")
                _assert("Season-adjusted confidence:" in response, f"adjusted confidence missing for prompt {i}")
                before_5 = re.split(r"(?m)^5\)", response, maxsplit=1)[0]
                checklist_area = re.split(r"(?m)^4\)", before_5, maxsplit=1)[-1]
                bullets = [ln for ln in checklist_area.splitlines() if ln.strip().startswith(("-", "*", "•"))]
                _assert(len(bullets) == 3, f"action checklist must have exactly 3 bullets for prompt {i}")
                _assert("recommendation" in data, f"recommendation missing for prompt {i}")
                _assert(data["recommendation"]["final_crop"] == "maize", "unexpected final crop in llm endpoint")

        for name, fn in [
            ("agent_health", t_health),
            ("agent_tools", t_tools),
            ("agent_llm_health", t_llm_health),
            ("agent_recommend_direct", t_recommend_direct),
            ("agent_recommend_location", t_recommend_location_enrichment),
            ("agent_missing_npk", t_missing_npk_rejected),
            ("agent_llm_false_prompt_no_tools", t_llm_false_prompt_no_tools),
            ("agent_llm_tool_prompt_location", t_llm_tool_prompt_location_calls_tools),
            ("agent_llm_prompt_template_shape", t_llm_prompt_template_shape),
            ("agent_llm_varied_prompts", t_llm_prompts_variety),
        ]:
            _run_check(name, fn, results)
    finally:
        patches.restore_all()


def run_optional_live_llm_probe(results: list[CheckResult]) -> None:
    def t_live_llm_probe() -> None:
        try:
            info = agent_main.llm_client.healthcheck()
        except Exception as exc:  # noqa: BLE001
            raise AssertionError(f"SKIPPED (live LLM unavailable): {exc}")
        _assert("available_models" in info, "live LLM health payload missing fields")

    _run_check("optional_live_llm_probe", t_live_llm_probe, results)


def print_summary(results: list[CheckResult]) -> int:
    failed = [r for r in results if not r.ok and not r.detail.startswith("SKIPPED")]
    skipped = [r for r in results if (not r.ok and r.detail.startswith("SKIPPED"))]

    print("=== EXTENSIVE SYSTEM TEST SUMMARY ===")
    print(f"Total checks: {len(results)}")
    print(f"Passed: {len(results) - len(failed) - len(skipped)}")
    print(f"Skipped: {len(skipped)}")
    print(f"Failed: {len(failed)}")

    if skipped:
        print("\n=== SKIPPED ===")
        for s in skipped:
            print(f"- {s.name}: {s.detail}")

    if failed:
        print("\n=== FAILURES ===")
        for f in failed:
            print(f"- {f.name}: {f.detail}")
        return 1

    print("\nOK: All required API + orchestration + LLM prompt-path tests passed.")
    return 0


def main() -> None:
    results: list[CheckResult] = []
    run_model_api_tests(results)
    run_agent_api_tests(results)
    run_optional_live_llm_probe(results)
    raise SystemExit(print_summary(results))


if __name__ == "__main__":
    main()
