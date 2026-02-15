from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

from api.prompts import build_system_prompt, build_user_prompt
from api.schemas import AgentRequest, AgentResponse, FeatureValue, LLMAdvisoryRequest, LLMAdvisoryResponse
from core import settings
from core.archive import new_run_context, write_json, write_text
from model_service.predict_xai_client import PredictXAIClient
from services.geocode import geocode_location
from services.icar_rag_reranker import rerank_with_icar_rag
from services.llm_local import LocalLLMClient
from services.rag import rag_search
from services.soil_soilgrids import get_soil_properties
from services.weather_openmeteo import get_weather

FEATURES = ["N", "P", "K", "temperature", "humidity", "ph"]
EPS = 0.05
XAI_REPORT_PATH = Path("xai_eval") / "report.json"
XAI_CURVES_PATH = Path("xai_eval") / "curves.json"
CALIBRATION_REPORT_PATH = Path("xai_eval") / "calibration_report.json"

app = FastAPI(title="LLM Integrated Crop Agent API", version="1.3.0")
model_client = PredictXAIClient(base_url=settings.model_api_base_url)
llm_client = LocalLLMClient()


# Deprecated compatibility shim. Calendar reranking logic has been removed.
def get_crop_calendar(region: str, month: int) -> dict[str, float]:
    _ = (region, month)
    return {}


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_xai_metrics() -> dict[str, Any]:
    report = _load_json_if_exists(XAI_REPORT_PATH)
    calibration = _load_json_if_exists(CALIBRATION_REPORT_PATH)
    return {"report": report, "calibration": calibration}


def _load_xai_curves() -> dict[str, Any]:
    return _load_json_if_exists(XAI_CURVES_PATH)


def _init_provenance(payload: AgentRequest) -> dict[str, FeatureValue]:
    provenance: dict[str, FeatureValue] = {}
    for feature in FEATURES:
        value = getattr(payload, feature)
        if value is not None:
            provenance[feature] = FeatureValue(value=float(value), source="user")
    return provenance


def _collect_features(
    payload: AgentRequest,
    *,
    no_tools_mode: bool,
) -> tuple[dict[str, float], dict[str, FeatureValue], list[str], str, list[str], dict[str, Any] | None]:
    warnings: list[str] = []
    tool_calls: list[str] = []
    provenance = _init_provenance(payload)

    missing_npk = [f for f in ["N", "P", "K"] if f not in provenance]
    if missing_npk:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Missing required N/P/K values. Cannot fabricate these features.",
                "missing_features": missing_npk,
                "hint": "Provide soil test values for N, P, K.",
            },
        )

    if no_tools_mode:
        missing = [f for f in FEATURES if f not in provenance]
        if missing:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "No-tools mode requires all model features to be provided directly.",
                    "missing_features": missing,
                },
            )
        return ({k: v.value for k, v in provenance.items()}, provenance, warnings, payload.region or "global", tool_calls, None)

    if all(feature in provenance for feature in FEATURES):
        return ({k: v.value for k, v in provenance.items()}, provenance, warnings, payload.region or "global", tool_calls, None)

    if not payload.location:
        missing = [f for f in FEATURES if f not in provenance]
        raise HTTPException(
            status_code=400,
            detail={"message": "Missing required features and no location provided.", "missing_features": missing},
        )

    geo = geocode_location(payload.location)
    tool_calls.append("geocode_location")
    region = payload.region or geo.get("region") or "global"

    missing_weather = [f for f in ["temperature", "humidity"] if f not in provenance]
    if missing_weather:
        weather = get_weather(geo["lat"], geo["lon"])
        tool_calls.append("get_weather")
        if "temperature" in missing_weather and weather.get("temperature") is not None:
            provenance["temperature"] = FeatureValue(value=float(weather["temperature"]), source="weather_api")
        if "humidity" in missing_weather and weather.get("humidity") is not None:
            provenance["humidity"] = FeatureValue(value=float(weather["humidity"]), source="weather_api")
        warnings.append("Weather values are estimated from Open-Meteo current conditions.")

    if "ph" not in provenance:
        soil = get_soil_properties(geo["lat"], geo["lon"])
        tool_calls.append("get_soil_properties")
        if soil.get("ph") is not None:
            provenance["ph"] = FeatureValue(value=float(soil["ph"]), source="soil_api")
        else:
            provenance["ph"] = FeatureValue(value=6.5, source="soil_api_fallback")
            warnings.append("SoilGrids pH unavailable at this point; using fallback pH=6.5.")
        warnings.append("Soil values are estimated from SoilGrids.")

    missing_any = [f for f in FEATURES if f not in provenance]
    if missing_any:
        raise HTTPException(status_code=400, detail={"message": "Feature enrichment incomplete.", "missing_features": missing_any})

    return ({k: v.value for k, v in provenance.items()}, provenance, warnings, region, tool_calls, geo)


def _data_quality_factor(provenance: dict[str, FeatureValue]) -> float:
    if any(v.source == "soil_api_fallback" for v in provenance.values()):
        return 0.75
    if any(v.source == "soil_api" for v in provenance.values()):
        return 0.85
    if any(v.source == "weather_api" for v in provenance.values()):
        return 0.90
    return 1.0


def _disagreement_metrics(model_response: dict[str, Any]) -> dict[str, Any]:
    models = model_response.get("models", {})
    preds = {m: str(v.get("prediction", {}).get("crop", "")).lower() for m, v in models.items()}
    confs = [float(v.get("prediction", {}).get("confidence", 0.0)) for v in models.values()]
    all_three_agree = len(set(preds.values())) == 1 if preds else True
    pairwise = {}
    keys = list(preds.keys())
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            k = f"{keys[i]}=={keys[j]}"
            pairwise[k] = preds[keys[i]] == preds[keys[j]]
    prob_std = float((sum((c - (sum(confs) / max(len(confs), 1))) ** 2 for c in confs) / max(len(confs), 1)) ** 0.5) if confs else 0.0
    disagreement_detected = (not all_three_agree) or (prob_std > 0.15)
    return {
        "all_three_agree": all_three_agree,
        "pairwise_agreement": pairwise,
        "prob_std": prob_std,
        "disagreement_detected": disagreement_detected,
    }


def _build_llm_curves(base_output: dict[str, Any], final_top: dict[str, Any], adjusted_confidence: float) -> dict[str, Any]:
    curves = base_output.get("curves", {})
    topk_curve = curves.get("topk_confidence", {})
    topk_x = topk_curve.get("x", [x["crop"] for x in base_output.get("top3", [])])
    topk_y = topk_curve.get("y", [float(x["confidence"]) for x in base_output.get("top3", [])])

    shap_sorted = base_output.get("shap", {}).get("sorted_by_abs", [])
    abs_vals = [float(x.get("abs_value", 0.0)) for x in shap_sorted]
    total = sum(abs_vals) if abs_vals else 0.0
    cum = []
    run = 0.0
    for v in abs_vals:
        run += v
        cum.append((run / total) if total > 0 else 0.0)

    return {
        "decision_stages": {
            "x": ["raw_model", "rag_rerank", "final"],
            "y": [
                float(base_output.get("prediction", {}).get("confidence", 0.0)),
                float(final_top.get("raw_model_confidence", 0.0)),
                float(adjusted_confidence),
            ],
        },
        "topk_confidence": {"x": topk_x, "y": topk_y},
        "shap_cumulative": {
            "x": list(range(1, len(cum) + 1)),
            "y": cum,
            "feature_order": [str(x.get("feature", "")) for x in shap_sorted],
        },
    }


def _contains_no_tools_directive(query: str) -> bool:
    low = query.lower()
    patterns = [
        r"\bdo not (?:call|use).{0,20}\btools?\b",
        r"\bdon't (?:call|use).{0,20}\btools?\b",
        r"\bno tools\b",
        r"\bwithout tools\b",
    ]
    return any(re.search(p, low) for p in patterns)


def _render_template_response(rec: AgentResponse) -> str:
    conflict_line = ""
    if rec.rerank_conflict:
        conflict_line = (
            f" Model preferred {rec.rerank_conflict['previous_top_crop']} (raw prob high) "
            f"but reranker suitability reduced it, so final is {rec.final_crop}."
        )

    lines: list[str] = []
    lines.append("1) Final recommended crop + short reason")
    lines.append(f"{rec.final_crop.capitalize()} is selected after ICAR RAG reranking.{conflict_line}")
    lines.append("")
    lines.append("2) Confidence interpretation")
    lines.append(f"Raw model confidence (from ML): {rec.raw_model_confidence:.4f}")
    lines.append(f"Season-adjusted confidence: {rec.adjusted_confidence:.4f} (after ICAR RAG rerank). Threshold reference: 0.60")
    lines.append("")
    lines.append("3) Top-3 tradeoff note (if available)")
    lines.append("; ".join(f"{i['crop']} (raw={i['raw_model_confidence']:.4f}, suit={i['rag_suitability']:.2f}, adj={i['adjusted_confidence']:.4f})" for i in rec.top3[:3]))
    lines.append("")
    lines.append("4) Action checklist")
    lines.append("- Verify N/P/K with a fresh soil lab test before planting.")
    lines.append("- Validate local weather and irrigation conditions against current season.")
    lines.append("- Start with a pilot plot before full-scale planting.")
    lines.append("")
    lines.append("5) Risk warning")
    if rec.adjusted_confidence < 0.6:
        lines.append("Low-confidence recommendation. Use conservative plan and manual agronomy review.")
    else:
        lines.append("No high-risk warning: adjusted confidence is at or above threshold.")
    return "\n".join(lines)


def _validate_llm_output(text: str, adjusted_confidence: float, tool_calls: list[str]) -> tuple[bool, str, dict[str, Any]]:
    low = text.lower()
    banned = ["okay, let me", "i need to", "let me think", "i will now"]
    cot_leak = any(b in low for b in banned)

    section_ok = all(k in text for k in ["1)", "2)", "3)", "4)", "5)"])
    confidence_terms_ok = ("raw model confidence" in low) and ("season-adjusted confidence" in low)

    section4 = re.split(r"\n5\)", text, maxsplit=1)[0]
    section4 = section4.split("\n4)", 1)[-1] if "\n4)" in text else section4
    bullets = [ln for ln in section4.splitlines() if ln.strip().startswith(("-", "*", "•"))]
    bullets_ok = len(bullets) == 3

    mentioned_tools = {t for t in ["geocode_location", "get_weather", "get_soil_properties"] if t in low}
    invalid_mentions = sorted(mentioned_tools.difference(set(tool_calls)))

    valid = True
    reason = "ok"
    if cot_leak:
        valid = False
        reason = "Contains internal reasoning leak"
    elif not section_ok:
        valid = False
        reason = "Missing required sections"
    elif not confidence_terms_ok:
        valid = False
        reason = "Missing raw/adjusted confidence terms"
    elif not bullets_ok:
        valid = False
        reason = "Action checklist must contain exactly 3 bullet points"
    elif invalid_mentions:
        valid = False
        reason = f"Mentions tools not called: {invalid_mentions}"
    elif adjusted_confidence < 0.6 and "risk warning" not in low:
        valid = False
        reason = "Missing risk warning for low confidence"

    return valid, reason, {
        "format_ok": section_ok,
        "cot_leak": cot_leak,
        "bullets_ok": bullets_ok,
        "confidence_terms_ok": confidence_terms_ok,
        "invalid_tool_mentions": invalid_mentions,
    }


def _recommend_core(payload: AgentRequest, *, no_tools_mode: bool) -> AgentResponse:
    features, provenance, warnings, region, tool_calls, geo = _collect_features(payload, no_tools_mode=no_tools_mode)

    model_response = model_client.predict(features=features, models=payload.models, top_k=payload.top_k)
    agreement = _disagreement_metrics(model_response)
    disagreement_multiplier = 0.85 if agreement["disagreement_detected"] else 1.0

    base_model = "xgboost" if "xgboost" in model_response["models"] else payload.models[0]
    base_output = model_response["models"][base_model]

    month = payload.month or datetime.utcnow().month
    if no_tools_mode:
        rerank = {
            "season": "unknown",
            "zone_resolution": "unknown",
            "zone_id": None,
            "zone_state": None,
            "zone_district": None,
            "zone_match": None,
            "queries": [],
            "retrieval_hits": [],
            "adjusted_topk": [
                {
                    "crop": str(x["crop"]).lower(),
                    "raw_model_confidence": float(x["confidence"]),
                    "rag_suitability": 1.0,
                    "adjusted_confidence": float(x["confidence"]),
                    "explanation_tokens": {"suitability_token": "FORCED_NO_TOOLS", "risk_tokens": "", "source": ""},
                }
                for x in base_output.get("top3", [])
            ],
            "rerank_conflict": None,
        }
    else:
        rerank = rerank_with_icar_rag(
            topk=base_output["top3"],
            features=features,
            location=payload.location,
            region=region,
            month=month,
            lat=(float(geo["lat"]) if geo and geo.get("lat") is not None else None),
            lon=(float(geo["lon"]) if geo and geo.get("lon") is not None else None),
            eps=EPS,
        )

    dq_factor = _data_quality_factor(provenance)

    adjusted_topk = []
    for item in rerank["adjusted_topk"]:
        adj = float(item["raw_model_confidence"]) * (float(item["rag_suitability"]) + EPS) * dq_factor * disagreement_multiplier
        adjusted_topk.append({**item, "adjusted_confidence": float(adj)})

    adjusted_topk.sort(key=lambda x: x["adjusted_confidence"], reverse=True)
    final_top = adjusted_topk[0]

    final_crop = str(final_top["crop"]).lower()
    raw_model_confidence = float(base_output.get("prediction", {}).get("confidence", final_top["raw_model_confidence"]))
    rag_suitability = float(final_top["rag_suitability"])
    adjusted_confidence = float(final_top["adjusted_confidence"])

    if rerank.get("rerank_conflict"):
        warnings.append("RAG rerank changed the top recommendation.")
    if rerank.get("zone_resolution") in {"state", "unknown"}:
        warnings.append("Localization strength is limited; rerank based on coarse zone match.")
    if agreement["disagreement_detected"]:
        warnings.append("Model disagreement detected.")
    if adjusted_confidence < 0.6:
        warnings.append("Low confidence recommendation (<0.6). Consider manual agronomy review.")

    xai_eval = _load_xai_metrics()
    llm_curves = _build_llm_curves(base_output=base_output, final_top=final_top, adjusted_confidence=adjusted_confidence)

    rag_rerank = {
        "season": rerank.get("season"),
        "zone_resolution": rerank.get("zone_resolution"),
        "zone_id": rerank.get("zone_id"),
        "zone_state": rerank.get("zone_state"),
        "zone_district": rerank.get("zone_district"),
        "queries": rerank.get("queries", []),
        "per_crop_suitability": {x["crop"]: x["rag_suitability"] for x in adjusted_topk},
        "retrieval_hits": rerank.get("retrieval_hits", []),
        "zone_match": rerank.get("zone_match"),
    }

    return AgentResponse(
        final_crop=final_crop,
        confidence=adjusted_confidence,
        raw_model_confidence=raw_model_confidence,
        rag_suitability=rag_suitability,
        adjusted_confidence=adjusted_confidence,
        eps=EPS,
        calendar_suitability=rag_suitability,
        top3=adjusted_topk[:3],
        shap=base_output["shap"],
        lime=base_output["lime"],
        curves=base_output.get("curves", {}),
        llm_curves=llm_curves,
        xai_eval=xai_eval,
        rag_rerank=rag_rerank,
        calendar_adjustment={
            "region": region,
            "month": month,
            "suitability": {x["crop"]: x["rag_suitability"] for x in adjusted_topk},
            "details": {"raw_topk": base_output.get("top3", []), "adjusted_topk": adjusted_topk},
            "base_model": base_model,
            "conflict": rerank.get("rerank_conflict") is not None,
        },
        rerank_conflict=rerank.get("rerank_conflict"),
        zone_resolution=str(rerank.get("zone_resolution") or "unknown"),
        zone_id=rerank.get("zone_id"),
        calendar_conflict=rerank.get("rerank_conflict"),
        deprecation={
            "calendar_suitability": "Deprecated alias. Use rag_suitability.",
            "calendar_conflict": "Deprecated alias. Use rerank_conflict.",
        },
        agreement_metrics=agreement,
        confidence_components={
            "raw_model_confidence": raw_model_confidence,
            "rag_suitability": rag_suitability,
            "eps": EPS,
            "data_quality_factor": dq_factor,
            "disagreement_multiplier": disagreement_multiplier,
            "final_confidence": adjusted_confidence,
            # backward-compatible alias
            "calendar_term": rag_suitability + EPS,
        },
        provenance=provenance,
        tool_calls=tool_calls,
        warnings=warnings,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tools")
def tools() -> dict[str, Any]:
    return {
        "tools": [
            "get_crop_recommendation_xai",
            "geocode_location",
            "get_weather",
            "get_soil_properties",
            "get_icar_rag_rerank",
        ],
        "rules": [
            "If query says do not call tools, call no tools.",
            "If all features present, skip geocode/weather/soil.",
            "If N/P/K missing, return 400 and request soil test values.",
            "If location provided and temperature/humidity missing, call weather API.",
            "If location provided and pH missing, call soil API.",
        ],
    }


@app.get("/llm/health")
def llm_health() -> dict[str, Any]:
    try:
        return llm_client.healthcheck()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"LLM provider unavailable: {exc}") from exc


@app.get("/rag/health")
def rag_health() -> dict[str, str]:
    try:
        _ = rag_search("health", k=1, corpus_dir="rag_corpus/icar_zones")
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/rag/search")
def rag_search_api(payload: dict[str, Any]) -> dict[str, Any]:
    query = str(payload.get("query", ""))
    k = int(payload.get("k", 5))
    return {"query": query, "hits": rag_search(query, k=k, corpus_dir="rag_corpus/icar_zones")}


@app.get("/metrics/xai")
def metrics_xai() -> dict[str, Any]:
    return _load_xai_metrics()


@app.get("/metrics/xai_curves")
def metrics_xai_curves() -> dict[str, Any]:
    return _load_xai_curves()


@app.post("/recommend", response_model=AgentResponse)
def recommend(payload: AgentRequest) -> AgentResponse:
    return _recommend_core(payload, no_tools_mode=False)


@app.post("/recommend_with_llm", response_model=LLMAdvisoryResponse)
def recommend_with_llm(payload: LLMAdvisoryRequest) -> LLMAdvisoryResponse:
    no_tools_mode = _contains_no_tools_directive(payload.query)
    rec = _recommend_core(payload.recommendation_input, no_tools_mode=no_tools_mode)

    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(payload.query, rec.model_dump_json(indent=2))

    llm_text = ""
    llm_error = None
    valid_meta: dict[str, Any] = {}
    llm_rounds: dict[str, Any] = {"round1_text": "", "round2_text": "", "chosen_text": ""}

    try:
        llm_rounds["round1_text"] = llm_client.chat(system_prompt=system_prompt, user_prompt=user_prompt)
        ok, reason, meta = _validate_llm_output(llm_rounds["round1_text"], rec.adjusted_confidence, rec.tool_calls)
        valid_meta = meta
        if ok:
            llm_text = llm_rounds["round1_text"]
        else:
            fix_prompt = (
                "Fix formatting only. Keep same facts. Remove self-talk. "
                "Include raw+adjusted confidence and exactly 3 action bullets."
            )
            llm_rounds["round2_text"] = llm_client.chat(system_prompt=system_prompt, user_prompt=f"{fix_prompt}\n\n{llm_rounds['round1_text']}")
            ok2, reason2, meta2 = _validate_llm_output(llm_rounds["round2_text"], rec.adjusted_confidence, rec.tool_calls)
            valid_meta = meta2
            if ok2:
                llm_text = llm_rounds["round2_text"]
                rec.warnings.append("round2 refinement applied")
            else:
                llm_error = f"validation_failed: {reason}; round2: {reason2}"
                llm_text = _render_template_response(rec)
    except Exception as exc:  # provider failure fallback
        llm_error = str(exc)
        llm_text = _render_template_response(rec)

    if llm_error:
        rec.warnings.append(f"LLM fallback applied: {llm_error}")

    llm_rounds["chosen_text"] = llm_text

    ctx = new_run_context("recommend_with_llm")
    run_dir = ctx["run_dir"]
    write_json(run_dir, "request.json", {
        "request_id": ctx["request_id"],
        "timestamp": ctx["timestamp"],
        "endpoint_name": ctx["endpoint_name"],
        "query": payload.query,
        "recommendation_input": payload.recommendation_input.model_dump(),
    })
    write_json(run_dir, "prompts.json", {"system_prompt": system_prompt, "user_prompt": user_prompt})
    write_json(run_dir, "tool_calls.json", rec.tool_calls)
    write_json(run_dir, "recommendation.json", rec.model_dump())
    write_json(run_dir, "validation.json", {"valid": llm_error is None, **valid_meta})
    write_json(run_dir, "llm_rounds.json", llm_rounds)
    write_text(run_dir, "llm_response.txt", llm_text)

    rr = rec.rag_rerank
    write_json(run_dir, "rag_hits.json", rr.get("retrieval_hits", []))
    write_json(run_dir, "icar_zone_match.json", {
        "zone_resolution": rec.zone_resolution,
        "zone_id": rec.zone_id,
        "zone_state": rr.get("zone_state"),
        "zone_district": rr.get("zone_district"),
        "zone_match": rr.get("zone_match"),
    })
    write_json(run_dir, "rag_rerank.json", rr)

    return LLMAdvisoryResponse(recommendation=rec, llm_response=llm_text, archive_run_dir=run_dir)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8100, reload=False)
