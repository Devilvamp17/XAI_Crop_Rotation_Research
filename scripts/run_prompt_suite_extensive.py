from __future__ import annotations

import argparse
import datetime as dt
import json
import secrets
from pathlib import Path
from typing import Any

import httpx

TOOL_NAMES = ["geocode_location", "get_weather", "get_soil_properties", "get_icar_rag_rerank"]
BANNED_COT = ["okay, let me", "i need to", "let me think", "i will now"]


def _direct_input(n: float, p: float, k: float, t: float, h: float, ph: float) -> dict[str, Any]:
    return {"N": n, "P": p, "K": k, "temperature": t, "humidity": h, "ph": ph, "top_k": 3}


def _location_input(location: str, n: float, p: float, k: float) -> dict[str, Any]:
    return {"location": location, "N": n, "P": p, "K": k, "top_k": 3}


def build_prompt_suite() -> list[dict[str, Any]]:
    prompts: list[dict[str, Any]] = []

    categories = [
        "standard_summary",
        "farmer_simple",
        "risk_uncertainty",
        "technical_xai",
        "rerank_conflict",
        "location_enrichment",
        "missing_inputs",
        "no_tools_directive",
    ]

    for i in range(5):
        prompts.append(
            {
                "id": f"A{i+1}",
                "category": "standard_summary",
                "query": "Provide a strict 5-section crop recommendation summary.",
                "recommendation_input": _direct_input(88 + i, 40, 42, 26.1, 70.2, 6.5),
                "expected_tools": ["get_icar_rag_rerank"],
                "expected_status": 200,
            }
        )
        prompts.append(
            {
                "id": f"B{i+1}",
                "category": "farmer_simple",
                "query": "Explain for a small farmer in simple words with exactly 3 action bullets.",
                "recommendation_input": _direct_input(70, 30, 20 + i, 29.0, 62.0, 6.1),
                "expected_tools": ["get_icar_rag_rerank"],
                "expected_status": 200,
            }
        )
        prompts.append(
            {
                "id": f"C{i+1}",
                "category": "risk_uncertainty",
                "query": "Focus on uncertainty and when to avoid planting the top crop.",
                "recommendation_input": _direct_input(90, 42, 43, 25.6, 71.4, 6.4),
                "expected_tools": ["get_icar_rag_rerank"],
                "expected_status": 200,
            }
        )
        prompts.append(
            {
                "id": f"D{i+1}",
                "category": "technical_xai",
                "query": "Give technical SHAP/LIME explanation for an agronomy researcher.",
                "recommendation_input": _direct_input(110, 55, 65, 31.2, 78.0, 6.8),
                "expected_tools": ["get_icar_rag_rerank"],
                "expected_status": 200,
            }
        )
        prompts.append(
            {
                "id": f"E{i+1}",
                "category": "rerank_conflict",
                "query": "If calendar changes top crop, explain conflict clearly and suggest fallback.",
                "recommendation_input": _location_input("Delhi, India", 90, 42, 43),
                "expected_tools": ["geocode_location", "get_weather", "get_soil_properties", "get_icar_rag_rerank"],
                "expected_status": 200,
            }
        )
        prompts.append(
            {
                "id": f"F{i+1}",
                "category": "location_enrichment",
                "query": "Use location enrichment and explain confidence limits.",
                "recommendation_input": _location_input("Mumbai, India", 95, 45, 40),
                "expected_tools": ["geocode_location", "get_weather", "get_soil_properties", "get_icar_rag_rerank"],
                "expected_status": 200,
            }
        )
        prompts.append(
            {
                "id": f"G{i+1}",
                "category": "missing_inputs",
                "query": "I only know location. Decide the crop for me.",
                "recommendation_input": {"location": "Pune, India", "P": 30, "K": 25, "top_k": 3},
                "expected_tools": [],
                "expected_status": 400,
            }
        )
        prompts.append(
            {
                "id": f"H{i+1}",
                "category": "no_tools_directive",
                "query": "Do not use any tools. Provide concise recommendation.",
                "recommendation_input": _direct_input(84, 38, 36, 27.8, 68.5, 6.4),
                "expected_tools": [],
                "expected_status": 200,
            }
        )

    assert len(prompts) >= 40
    return prompts


def infer_tools_used(response_json: dict[str, Any]) -> list[str]:
    rec = response_json.get("recommendation", {})
    explicit = rec.get("tool_calls")
    if isinstance(explicit, list):
        return sorted(str(x) for x in explicit)

    tools: set[str] = set()
    prov = rec.get("provenance", {})
    if any(v.get("source") == "weather_api" for v in prov.values()):
        tools.add("get_weather")
    if any(v.get("source") in {"soil_api", "soil_api_fallback"} for v in prov.values()):
        tools.add("get_soil_properties")
    if rec.get("rag_rerank"):
        tools.add("get_icar_rag_rerank")
    if any(str(v.get("source", "")).endswith("api") for v in prov.values()):
        tools.add("geocode_location")
    return sorted(tools)


def score_output(entry: dict[str, Any]) -> dict[str, Any]:
    if not entry.get("ok"):
        return {
            "format_ok": False,
            "no_cot_leak": False,
            "raw_and_adjusted_confidence_present": False,
            "has_3_bullets_only": False,
            "rerank_conflict_explained_when_needed": False,
            "mentions_top_shap_feature_when_available": False,
            "tools_used_match_expected": False,
            "refusal_correct_when_missing_npk": bool(entry.get("status_code") == 400),
            "length_ok": False,
            "required_hits": 0,
            "optional_hits": 0,
            "penalties": 40,
            "quality_score": 0,
        }

    resp = entry["response"]
    rec = resp["recommendation"]
    text = str(resp.get("llm_response", ""))
    low = text.lower()

    format_ok = all(f"{i})" in text for i in [1, 2, 3, 4, 5])
    no_cot_leak = not any(k in low for k in BANNED_COT)
    raw_adj = ("raw" in low) and ("adjusted" in low) and ("confidence" in low)

    section4 = text.split("\n5)", 1)[0]
    section4 = section4.split("\n4)", 1)[-1] if "\n4)" in text else section4
    bullets = [ln for ln in section4.splitlines() if ln.strip().startswith(("-", "*", "•"))]
    bullets_ok = len(bullets) == 3

    conflict_needed = bool(rec.get("rerank_conflict"))
    conflict_ok = (not conflict_needed) or (("model preferred" in low and "final" in low) or ("calendar" in low and "final" in low))

    top_shap = rec.get("shap", {}).get("sorted_by_abs", [])
    top_feat = str(top_shap[0].get("feature", "")).lower() if top_shap else ""
    shap_ok = (not top_feat) or (top_feat in low)

    expected = set(entry.get("expected_tools", []))
    used = set(entry.get("inferred_tools_used", []))
    tools_ok = expected.issubset(used) if entry.get("category") != "no_tools_directive" else len(used) == 0

    missing_npk_refusal = entry.get("category") != "missing_inputs" or entry.get("status_code") == 400

    length_ok = 80 <= len(text) <= 6000

    required_checks = [format_ok, no_cot_leak, raw_adj, bullets_ok, tools_ok, missing_npk_refusal]
    optional_checks = [conflict_ok, shap_ok, length_ok]
    penalties = 0
    if not length_ok:
        penalties += 5
    if not tools_ok:
        penalties += 10
    if not no_cot_leak:
        penalties += 20

    required_hits = sum(1 for x in required_checks if x)
    optional_hits = sum(1 for x in optional_checks if x)
    quality_score = max(0, min(100, required_hits * 30 + optional_hits * 10 - penalties))

    return {
        "format_ok": format_ok,
        "no_cot_leak": no_cot_leak,
        "raw_and_adjusted_confidence_present": raw_adj,
        "has_3_bullets_only": bullets_ok,
        "rerank_conflict_explained_when_needed": conflict_ok,
        "mentions_top_shap_feature_when_available": shap_ok,
        "tools_used_match_expected": tools_ok,
        "refusal_correct_when_missing_npk": missing_npk_refusal,
        "length_ok": length_ok,
        "required_hits": required_hits,
        "optional_hits": optional_hits,
        "penalties": penalties,
        "quality_score": quality_score,
    }


def render_md(results: list[dict[str, Any]], suite_id: str, agent_api: str) -> str:
    lines = [
        "# Extensive Prompt Suite Results",
        "",
        f"Suite ID: `{suite_id}`",
        f"Generated: {dt.datetime.utcnow().isoformat()}Z",
        f"Agent API: `{agent_api}`",
        "",
    ]
    for r in results:
        lines += [
            f"## {r['id']} ({r['category']})",
            "",
            f"> {r['query']}",
            "",
            f"- Status: `{r['status_code']}`",
            f"- Quality Score: `{r['score']['quality_score']}`",
            f"- Tools: `{r.get('inferred_tools_used', [])}`",
            "",
        ]
    return "\n".join(lines)


def run_suite(agent_api: str, out_root: Path) -> int:
    suite_id = f"suite_ext_{secrets.token_hex(4)}"
    suite_dir = out_root / suite_id
    suite_dir.mkdir(parents=True, exist_ok=True)

    prompts = build_prompt_suite()
    (suite_dir / "prompts.json").write_text(json.dumps(prompts, indent=2), encoding="utf-8")

    results: list[dict[str, Any]] = []
    with httpx.Client(timeout=300.0) as client:
        client.get(f"{agent_api.rstrip('/')}/health").raise_for_status()

        for p in prompts:
            body = {
                "query": p["query"],
                "recommendation_input": p["recommendation_input"],
            }
            row = {
                "id": p["id"],
                "category": p["category"],
                "query": p["query"],
                "expected_tools": p["expected_tools"],
                "expected_status": p["expected_status"],
                "request": body,
            }
            try:
                r = client.post(f"{agent_api.rstrip('/')}/recommend_with_llm", json=body)
                row["status_code"] = r.status_code
                if r.status_code == 200:
                    data = r.json()
                    row["ok"] = True
                    row["response"] = data
                    row["inferred_tools_used"] = infer_tools_used(data)
                else:
                    row["ok"] = False
                    row["error"] = r.json() if "application/json" in r.headers.get("content-type", "") else r.text
            except Exception as exc:  # noqa: BLE001
                row["ok"] = False
                row["status_code"] = None
                row["error"] = str(exc)

            row["score"] = score_output(row)
            results.append(row)

    (suite_dir / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (suite_dir / "results.md").write_text(render_md(results, suite_id=suite_id, agent_api=agent_api), encoding="utf-8")

    by_cat: dict[str, list[float]] = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(float(r["score"]["quality_score"]))

    compliance = {
        "suite_id": suite_id,
        "cases_total": len(results),
        "cases_passed_http": sum(1 for r in results if r.get("status_code") == 200),
        "category_average_quality": {k: (sum(v) / len(v) if v else 0.0) for k, v in by_cat.items()},
        "metrics": {
            "format_ok": sum(1 for r in results if r["score"].get("format_ok")),
            "no_cot_leak": sum(1 for r in results if r["score"].get("no_cot_leak")),
            "raw_and_adjusted_confidence_present": sum(
                1 for r in results if r["score"].get("raw_and_adjusted_confidence_present")
            ),
            "has_3_bullets_only": sum(1 for r in results if r["score"].get("has_3_bullets_only")),
            "rerank_conflict_explained_when_needed": sum(
                1 for r in results if r["score"].get("rerank_conflict_explained_when_needed")
            ),
            "mentions_top_shap_feature_when_available": sum(
                1 for r in results if r["score"].get("mentions_top_shap_feature_when_available")
            ),
            "tools_used_match_expected": sum(1 for r in results if r["score"].get("tools_used_match_expected")),
            "refusal_correct_when_missing_npk": sum(
                1 for r in results if r["score"].get("refusal_correct_when_missing_npk")
            ),
            "length_ok": sum(1 for r in results if r["score"].get("length_ok")),
        },
    }
    (suite_dir / "compliance_summary.json").write_text(json.dumps(compliance, indent=2), encoding="utf-8")

    print(f"Suite directory: {suite_dir}")
    print(f"Total prompts: {len(results)}")
    print(f"HTTP 200: {compliance['cases_passed_http']}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run extensive prompt suite")
    parser.add_argument("--agent-api", default="http://127.0.0.1:8100")
    parser.add_argument("--out-root", default="artifacts/suites")
    args = parser.parse_args()
    raise SystemExit(run_suite(agent_api=args.agent_api, out_root=Path(args.out_root)))


if __name__ == "__main__":
    main()
