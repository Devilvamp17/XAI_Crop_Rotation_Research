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
from model_service.predict_xai_client import PredictXAIClient
from services.crop_calendar import get_crop_calendar
from services.geocode import geocode_location
from services.llm_local import LocalLLMClient
from services.soil_soilgrids import get_soil_properties
from services.weather_openmeteo import get_weather

FEATURES = ["N", "P", "K", "temperature", "humidity", "ph"]
EPS = 0.05
XAI_REPORT_PATH = Path("xai_eval") / "report.json"
XAI_LEGACY_REPORT_PATH = Path("xai_eval") / "evaluation_report.json"
CALIBRATION_REPORT_PATH = Path("xai_eval") / "calibration_report.json"

app = FastAPI(title="LLM Integrated Crop Agent API", version="1.1.0")
model_client = PredictXAIClient(base_url=settings.model_api_base_url)
llm_client = LocalLLMClient()


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_xai_metrics() -> dict[str, Any]:
    report = _load_json_if_exists(XAI_REPORT_PATH)
    if not report:
        report = _load_json_if_exists(XAI_LEGACY_REPORT_PATH)
    calibration = _load_json_if_exists(CALIBRATION_REPORT_PATH)
    return {
        "report": report,
        "calibration": calibration,
    }


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
) -> tuple[dict[str, float], dict[str, FeatureValue], list[str], str, list[str]]:
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
        return ({k: v.value for k, v in provenance.items()}, provenance, warnings, payload.region or "global", tool_calls)

    if all(feature in provenance for feature in FEATURES):
        return ({k: v.value for k, v in provenance.items()}, provenance, warnings, payload.region or "global", tool_calls)

    if not payload.location:
        missing = [f for f in FEATURES if f not in provenance]
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Missing required features and no location provided.",
                "missing_features": missing,
            },
        )

    need_geo = payload.region is None or any(f not in provenance for f in ["temperature", "humidity", "ph"])
    geo = None
    if need_geo:
        geo = geocode_location(payload.location)
        tool_calls.append("geocode_location")

    region = payload.region or (geo.get("region") if geo else None) or "global"

    missing_weather = [f for f in ["temperature", "humidity"] if f not in provenance]
    if missing_weather:
        if geo is None:
            geo = geocode_location(payload.location)
            tool_calls.append("geocode_location")
        weather = get_weather(geo["lat"], geo["lon"])
        tool_calls.append("get_weather")
        if "temperature" in missing_weather and weather.get("temperature") is not None:
            provenance["temperature"] = FeatureValue(value=float(weather["temperature"]), source="weather_api")
        if "humidity" in missing_weather and weather.get("humidity") is not None:
            provenance["humidity"] = FeatureValue(value=float(weather["humidity"]), source="weather_api")
        warnings.append("Weather values are estimated from Open-Meteo current conditions.")

    if "ph" not in provenance:
        if geo is None:
            geo = geocode_location(payload.location)
            tool_calls.append("geocode_location")
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
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Feature enrichment incomplete.",
                "missing_features": missing_any,
            },
        )

    return ({k: v.value for k, v in provenance.items()}, provenance, warnings, region, tool_calls)


def _rerank_with_calendar(topk: list[dict[str, Any]], suitability: dict[str, float], eps: float) -> dict[str, Any]:
    adjusted: list[dict[str, Any]] = []
    for item in topk:
        crop = str(item["crop"]).lower()
        raw = float(item["confidence"])
        suit = float(suitability.get(crop, 0.0))
        adj = raw * (suit + eps)
        adjusted.append(
            {
                "crop": crop,
                "raw_model_confidence": raw,
                "calendar_suitability": suit,
                "adjusted_confidence": adj,
            }
        )

    adjusted.sort(key=lambda x: x["adjusted_confidence"], reverse=True)
    return {"raw_topk": topk, "adjusted_topk": adjusted}


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
            "x": ["raw_model", "calendar_rerank", "final"],
            "y": [
                float(base_output.get("prediction", {}).get("confidence", 0.0)),
                float(final_top.get("raw_model_confidence", 0.0)),
                float(adjusted_confidence),
            ],
        },
        "topk_confidence": {
            "x": topk_x,
            "y": topk_y,
        },
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
    conflict = any("changed the top recommendation" in w.lower() for w in rec.warnings)
    conflict_line = ""
    if conflict and rec.top3:
        raw_pref = rec.calendar_adjustment.get("details", {}).get("raw_topk", [{}])[0].get("crop", "unknown")
        final = rec.final_crop
        raw_pref_suit = rec.calendar_adjustment.get("suitability", {}).get(str(raw_pref).lower(), 0.0)
        conflict_line = (
            f" Model preferred {raw_pref} (raw prob high) but calendar suitability was {raw_pref_suit:.2f}, "
            f"so final is {final}."
        )

    lines: list[str] = []
    lines.append("1) Final recommended crop + short reason")
    lines.append(f"{rec.final_crop.capitalize()} is selected after season-aware re-ranking.{conflict_line}")
    lines.append("")
    lines.append("2) Confidence interpretation")
    lines.append(f"Raw model confidence (from ML): {rec.raw_model_confidence:.4f}")
    lines.append(
        f"Season-adjusted confidence: {rec.adjusted_confidence:.4f} (after crop calendar). Threshold reference: 0.60"
    )
    lines.append("")
    lines.append("3) Top-3 tradeoff note (if available)")
    if rec.top3:
        lines.append(
            "; ".join(
                f"{i['crop']} (raw={i['raw_model_confidence']:.4f}, suit={i['calendar_suitability']:.2f}, adj={i['adjusted_confidence']:.4f})"
                for i in rec.top3[:3]
            )
        )
    else:
        lines.append("Top-3 not available.")
    lines.append("")
    lines.append("4) Action checklist")
    lines.append("- Verify N/P/K with a fresh soil lab test before planting.")
    lines.append("- Validate recent field weather against model assumptions.")
    lines.append("- Start with a pilot plot before full-scale planting.")
    lines.append("")
    lines.append("5) Risk warning")
    if rec.adjusted_confidence < 0.6:
        lines.append("Low-confidence recommendation. Use conservative plan, prefer in-season options, and do manual agronomy review.")
    else:
        lines.append("No high-risk warning: adjusted confidence is at or above threshold.")
    return "\n".join(lines)


def _validate_llm_output(text: str, adjusted_confidence: float, tool_calls: list[str]) -> tuple[bool, str]:
    low = text.lower()
    banned = ["okay, let me", "i need to", "let me think", "i will now"]
    if any(b in low for b in banned):
        return False, "Contains internal reasoning leak"

    if "1)" not in text or "2)" not in text or "3)" not in text or "4)" not in text or "5)" not in text:
        return False, "Missing required sections"

    if "raw model confidence" not in low or "season-adjusted confidence" not in low:
        return False, "Missing raw/adjusted confidence terms"

    section4 = re.split(r"\n5\)", text, maxsplit=1)[0]
    section4 = section4.split("\n4)", 1)[-1] if "\n4)" in text else section4
    bullets = [ln for ln in section4.splitlines() if ln.strip().startswith(("-", "*", "•"))]
    if len(bullets) != 3:
        return False, "Action checklist must contain exactly 3 bullet points"

    mentioned_tools = {
        t
        for t in ["geocode_location", "get_weather", "get_soil_properties", "get_crop_calendar"]
        if t in low
    }
    invalid_mentions = mentioned_tools.difference(set(tool_calls))
    if invalid_mentions:
        return False, f"Mentions tools not called: {sorted(invalid_mentions)}"

    if adjusted_confidence < 0.6 and "risk warning" not in low:
        return False, "Missing risk warning for low confidence"

    return True, "ok"


def _recommend_core(payload: AgentRequest, *, no_tools_mode: bool) -> AgentResponse:
    features, provenance, warnings, region, tool_calls = _collect_features(payload, no_tools_mode=no_tools_mode)

    model_response = model_client.predict(features=features, models=payload.models, top_k=payload.top_k)

    base_model = "xgboost" if "xgboost" in model_response["models"] else payload.models[0]
    base_output = model_response["models"][base_model]

    month = payload.month or datetime.utcnow().month
    if no_tools_mode:
        suitability = {str(x["crop"]).lower(): 1.0 for x in base_output.get("top3", [])}
    else:
        suitability = get_crop_calendar(region=region, month=month)
        tool_calls.append("get_crop_calendar")

    rerank = _rerank_with_calendar(base_output["top3"], suitability, eps=EPS)
    final_top = rerank["adjusted_topk"][0]

    final_crop = final_top["crop"]
    raw_model_confidence = float(base_output.get("prediction", {}).get("confidence", final_top["raw_model_confidence"]))
    calendar_suitability = float(final_top["calendar_suitability"])
    adjusted_confidence = float(final_top["adjusted_confidence"])

    raw_top1 = str(base_output["top3"][0]["crop"]).lower()
    if raw_top1 != final_crop:
        warnings.append("Calendar adjustment changed the top recommendation.")
    if adjusted_confidence < 0.6:
        warnings.append("Low confidence recommendation (<0.6). Consider manual agronomy review.")

    xai_eval = _load_xai_metrics()

    llm_curves = _build_llm_curves(base_output=base_output, final_top=final_top, adjusted_confidence=adjusted_confidence)

    return AgentResponse(
        final_crop=final_crop,
        confidence=adjusted_confidence,
        raw_model_confidence=raw_model_confidence,
        calendar_suitability=calendar_suitability,
        adjusted_confidence=adjusted_confidence,
        eps=EPS,
        top3=rerank["adjusted_topk"][:3],
        shap=base_output["shap"],
        lime=base_output["lime"],
        curves=base_output.get("curves", {}),
        llm_curves=llm_curves,
        xai_eval=xai_eval,
        calendar_adjustment={
            "region": region,
            "month": month,
            "suitability": suitability,
            "details": rerank,
            "base_model": base_model,
            "conflict": raw_top1 != final_crop,
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
            "get_crop_calendar",
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


@app.get("/metrics/xai")
def metrics_xai() -> dict[str, Any]:
    return _load_xai_metrics()


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
    try:
        llm_text = llm_client.chat(system_prompt=system_prompt, user_prompt=user_prompt)
        ok, reason = _validate_llm_output(llm_text, rec.adjusted_confidence, rec.tool_calls)
        if not ok:
            llm_error = f"validation_failed: {reason}"
            llm_text = _render_template_response(rec)
    except Exception as exc:  # fallback for provider/rate/payment failures
        llm_error = str(exc)
        llm_text = _render_template_response(rec)

    if llm_error:
        rec.warnings.append(f"LLM fallback applied: {llm_error}")

    return LLMAdvisoryResponse(recommendation=rec, llm_response=llm_text)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8100, reload=False)
