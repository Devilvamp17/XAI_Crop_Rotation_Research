from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import httpx

REQUIRED_SECTIONS = [
    "1)",
    "2)",
    "3)",
    "4)",
    "5)",
]
BANNED_COT = ["okay, let me", "i need to", "let me think", "i will now"]
TOOL_NAMES = ["geocode_location", "get_weather", "get_soil_properties", "get_icar_rag_rerank"]


def infer_tools_used(response_json: dict[str, Any]) -> list[str]:
    explicit = response_json.get("recommendation", {}).get("tool_calls")
    if isinstance(explicit, list):
        return sorted(str(x) for x in explicit)

    tools: set[str] = set()
    prov = response_json.get("recommendation", {}).get("provenance", {})
    for _, meta in prov.items():
        source = str(meta.get("source", ""))
        if source == "weather_api":
            tools.add("get_weather")
        if source in {"soil_api", "soil_api_fallback"}:
            tools.add("get_soil_properties")

    calendar_adj = response_json.get("recommendation", {}).get("rag_rerank", {})
    if calendar_adj:
        tools.add("get_icar_rag_rerank")

    if any(
        str(v.get("source", "")).endswith("api") or str(v.get("source", "")).endswith("fallback")
        for v in prov.values()
    ):
        tools.add("geocode_location")

    return sorted(tools)


def score_llm_output(text: str, inferred_tools: list[str], query: str) -> dict[str, Any]:
    low = text.lower()
    required_hits = sum(1 for k in REQUIRED_SECTIONS if k in text)
    cot_leaks = [p for p in BANNED_COT if p in low]
    has_raw = "raw model confidence" in low
    has_adjusted = "season-adjusted confidence" in low
    section4 = text.split("\n5)", 1)[0]
    section4 = section4.split("\n4)", 1)[-1] if "\n4)" in text else section4
    bullets = [ln for ln in section4.splitlines() if ln.strip().startswith(("-", "*", "•"))]
    mentioned_tools = {t for t in TOOL_NAMES if t in low}
    invalid_tool_mentions = sorted(mentioned_tools.difference(set(inferred_tools)))
    no_tools_query = "do not call tools" in query.lower() or "no tools" in query.lower() or "without tools" in query.lower()
    no_tools_violation = no_tools_query and bool(inferred_tools)
    length_ok = 80 <= len(text) <= 6000

    score = required_hits * 14
    score += 8 if has_raw else 0
    score += 8 if has_adjusted else 0
    score += 10 if len(bullets) == 3 else 0
    score += 10 if not cot_leaks else 0
    score += 10 if not invalid_tool_mentions else 0
    score += 10 if not no_tools_violation else 0
    score += 10 if length_ok else 0
    score = min(score, 100)
    return {
        "score": score,
        "required_hits": required_hits,
        "cot_leaks": cot_leaks,
        "has_raw_confidence": has_raw,
        "has_adjusted_confidence": has_adjusted,
        "checklist_bullet_count": len(bullets),
        "invalid_tool_mentions": invalid_tool_mentions,
        "no_tools_violation": no_tools_violation,
        "length_ok": length_ok,
    }


def render_markdown(entries: list[dict[str, Any]], model_api: str, agent_api: str) -> str:
    lines: list[str] = []
    lines.append("# LLM Prompt Test Outputs")
    lines.append("")
    lines.append(f"Generated: {dt.datetime.utcnow().isoformat()}Z")
    lines.append(f"Model API: `{model_api}`")
    lines.append(f"Agent API: `{agent_api}`")
    lines.append("")

    for item in entries:
        lines.append(f"## {item['id']}")
        lines.append("")
        lines.append("**Prompt**")
        lines.append("")
        lines.append(f"> {item['query']}")
        lines.append("")
        lines.append(f"- Expected HTTP: `{item.get('expected_status', 200)}`")

        if item.get("ok"):
            if item.get("status_code") == 200:
                rec = item["response"]["recommendation"]
                lines.append(f"- Final Crop: `{rec.get('final_crop')}`")
                lines.append(f"- Confidence: `{rec.get('confidence')}`")
                lines.append(f"- Warnings: `{rec.get('warnings', [])}`")
                lines.append(f"- Inferred Tools Used: `{item.get('inferred_tools_used', [])}`")
            else:
                lines.append(f"- Status: `PASSED (expected non-200)`")
                lines.append(f"- HTTP: `{item.get('status_code')}`")
                lines.append(f"- Response: `{item.get('response')}`")
            q = item.get("quality", {})
            lines.append(
                f"- Quality Score: `{q.get('score')}` (required_hits={q.get('required_hits')}, bullets={q.get('checklist_bullet_count')}, cot_leaks={q.get('cot_leaks')}, invalid_tool_mentions={q.get('invalid_tool_mentions')}, no_tools_violation={q.get('no_tools_violation')}, length_ok={q.get('length_ok')})"
            )
            lines.append("")
            lines.append("**LLM Output**")
            lines.append("")
            lines.append("```text")
            if item.get("status_code") == 200:
                lines.append(str(item["response"].get("llm_response", "")).strip())
            else:
                lines.append("N/A (expected non-200 case)")
            lines.append("```")
        else:
            lines.append(f"- Status: `FAILED`")
            lines.append(f"- HTTP: `{item.get('status_code')}`")
            lines.append(f"- Error: `{item.get('error')}`")
        lines.append("")

    return "\n".join(lines)


def run_suite(prompt_file: Path, out_json: Path, out_md: Path, model_api: str, agent_api: str) -> int:
    prompts = json.loads(prompt_file.read_text(encoding="utf-8"))
    entries: list[dict[str, Any]] = []

    with httpx.Client(timeout=300.0) as client:
        client.get(f"{model_api.rstrip('/')}/health").raise_for_status()
        client.get(f"{agent_api.rstrip('/')}/health").raise_for_status()

        for p in prompts:
            expected_status = int(p.get("expected_status", 200))
            body = {
                "query": p["query"],
                "recommendation_input": p["recommendation_input"],
            }
            entry = {
                "id": p["id"],
                "query": p["query"],
                "request": body,
                "expected_status": expected_status,
            }
            try:
                r = client.post(f"{agent_api.rstrip('/')}/recommend_with_llm", json=body)
                entry["status_code"] = r.status_code
                if r.status_code == expected_status:
                    entry["ok"] = True
                    if r.status_code == 200:
                        resp = r.json()
                        entry["response"] = resp
                        entry["inferred_tools_used"] = infer_tools_used(resp)
                        entry["quality"] = score_llm_output(
                            str(resp.get("llm_response", "")),
                            inferred_tools=entry["inferred_tools_used"],
                            query=p["query"],
                        )
                    else:
                        try:
                            entry["response"] = r.json()
                        except Exception:
                            entry["response"] = {"raw": r.text}
                        entry["inferred_tools_used"] = []
                        entry["quality"] = {
                            "score": 100,
                            "required_hits": 0,
                            "cot_leaks": [],
                            "has_raw_confidence": False,
                            "has_adjusted_confidence": False,
                            "checklist_bullet_count": 0,
                            "invalid_tool_mentions": [],
                            "no_tools_violation": False,
                            "length_ok": True,
                            "note": f"Non-200 response matched expected_status={expected_status}",
                        }
                elif r.status_code == 200:
                    resp = r.json()
                    entry["ok"] = False
                    entry["response"] = resp
                    entry["inferred_tools_used"] = infer_tools_used(resp)
                    entry["quality"] = score_llm_output(
                        str(resp.get("llm_response", "")),
                        inferred_tools=entry["inferred_tools_used"],
                        query=p["query"],
                    )
                    entry["error"] = {"message": f"Unexpected status: got 200 expected {expected_status}"}
                else:
                    entry["ok"] = False
                    try:
                        entry["error"] = r.json()
                    except Exception:
                        entry["error"] = r.text
            except Exception as exc:  # noqa: BLE001
                entry["ok"] = False
                entry["status_code"] = None
                entry["error"] = str(exc)
            entries.append(entry)

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    out_md.write_text(render_markdown(entries, model_api=model_api, agent_api=agent_api), encoding="utf-8")

    failed = [e for e in entries if not e.get("ok")]
    print(f"Prompt cases: {len(entries)} | Passed: {len(entries)-len(failed)} | Failed: {len(failed)}")
    print(f"JSON report: {out_json}")
    print(f"Markdown report: {out_md}")
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LLM prompt suite and save outputs")
    parser.add_argument("--prompts", default="prompts/llm_prompt_suite.json")
    parser.add_argument("--out-json", default="artifacts/llm_prompt_outputs.json")
    parser.add_argument("--out-md", default="artifacts/llm_prompt_outputs.md")
    parser.add_argument("--model-api", default="http://127.0.0.1:8000")
    parser.add_argument("--agent-api", default="http://127.0.0.1:8100")
    args = parser.parse_args()

    code = run_suite(
        prompt_file=Path(args.prompts),
        out_json=Path(args.out_json),
        out_md=Path(args.out_md),
        model_api=args.model_api,
        agent_api=args.agent_api,
    )
    raise SystemExit(code)


if __name__ == "__main__":
    main()
