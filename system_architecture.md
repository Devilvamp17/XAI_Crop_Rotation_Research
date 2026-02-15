# System Architecture

This document describes the complete architecture of the LLM-integrated crop recommendation platform.

## 1. High-Level Overview

The system is split into two APIs and several support modules:

1. Model API (`main.py`, port `8000`)
- Runs trained ML models
- Produces prediction, top-k probabilities, SHAP, LIME, and confidence curves

2. Agent API (`api/main.py`, port `8100`)
- Orchestrates feature enrichment, calendar-aware reranking, provenance, tool policy, and LLM advisory
- Adds reliability controls and fallback responses

3. Service adapters (`services/`)
- Geocoding: Nominatim
- Weather: Open-Meteo
- Soil: SoilGrids
- Crop calendar: local dataset lookup
- LLM provider adapter: local/Ollama, OpenRouter, OpenAI-compatible

4. Evaluation subsystem (`xai_eval/`)
- Offline computation of explanation quality and calibration metrics
- Exposed read-only via `/metrics/xai`

## 2. Component Map

```text
User / Client
   |
   | HTTP
   v
Agent API (8100) -----------------------> Model API Client -------------------> Model API (8000)
   |                                             |                                   |
   |                                             |                                   |--> xgboost/rf/lr models
   |                                             |                                   |--> SHAP explainers
   |                                             |                                   |--> LIME explainer
   |
   |--> Geocode Service (Nominatim)
   |--> Weather Service (Open-Meteo)
   |--> Soil Service (SoilGrids)
   |--> Calendar Service (local CSV)
   |
   |--> LLM Client (OpenRouter/OpenAI/Ollama)
   |
   +--> Response Builder (strict schema + warnings + llm_curves + provenance)

Offline:
xai_eval/evaluate.py --> report.json + calibration_report.json --> /metrics/xai
```

## 3. Request Flow: `/recommend`

Input schema (`AgentRequest`) accepts:
- Direct features: `N, P, K, temperature, humidity, ph`
- Or location-assisted input: `location`, optional `region`, optional `month`
- `models` list and `top_k`

Flow:
1. Validate required agronomy constraints.
- If any of `N/P/K` are missing -> return `400`.
- System never fabricates `N/P/K`.

2. Decide feature acquisition mode.
- If all model features present -> use user values directly.
- Else if location exists -> enrich missing weather/soil fields.
- Else -> `400` (insufficient features).

3. Track provenance for every feature.
- `user`
- `weather_api`
- `soil_api`
- `soil_api_fallback` (for pH fallback)

4. Call model API.
- `POST /predict` with selected models/top-k and resolved features.

5. Apply calendar re-ranking.
- Lookup suitability by `region` and `month`.
- Compute:
  - `raw_model_confidence` (from ML)
  - `calendar_suitability` in `[0..1]`
  - `adjusted_confidence = raw * (suitability + eps)`
- Sort top-k by `adjusted_confidence`.

6. Construct final response.
- `final_crop`, `top3`, `warnings`, `calendar_adjustment`
- `curves` (from model API)
- `llm_curves` (agent-computed grounded curves)
- `xai_eval` (cached metrics)

## 4. Request Flow: `/recommend_with_llm`

1. Run the same recommendation core as `/recommend`.
2. Build strict LLM prompts:
- No internal reasoning
- Exact 5-section format
- Must include raw + season-adjusted confidence
- Risk warning when adjusted confidence < 0.6

3. Call configured provider (`LLM_PROVIDER`).
4. Validate output:
- Reject chain-of-thought leaks (`Okay, let me...`, `I need to...`)
- Require sections `1)`..`5)`
- Require confidence terms
- Enforce exactly 3 checklist bullets
- Reject mention of tools that were not actually called

5. Fallback behavior:
- If provider fails or output fails validation, generate deterministic template advisory from structured response JSON.

## 5. Tool-Routing Policy

Implemented routing rules:

1. No-tools directive
- If user query contains phrases like `do not use tools` / `do not call tools` / `no tools`, agent enters no-tools mode.
- No external tool calls are made.
- In no-tools mode, all required features must be present.

2. Complete direct features
- Skip geocode/weather/soil tools.

3. Missing N/P/K
- Return `400` with actionable hint.

4. Location + missing temperature/humidity
- Geocode + weather call.

5. Location + missing pH
- Geocode + soil call.

## 6. External Integrations

### 6.1 Geocoding
- Provider: OpenStreetMap Nominatim
- Usage: `location -> lat/lon/region`
- Safeguard: user-agent + caching/rate control in service layer

### 6.2 Weather
- Provider: Open-Meteo
- Usage: fetch current `temperature` and `humidity` for model features
- Marked as estimated in warnings/provenance

### 6.3 Soil
- Provider: ISRIC SoilGrids
- Usage: fetch pH when missing
- If unavailable, fallback to pH=6.5 with explicit warning

### 6.4 Crop Calendar
- Provider: local CSV lookup
- Purpose: season-aware suitability score per crop

## 7. Confidence Semantics

Three confidence values are intentionally separated:

1. Raw model confidence
- Probability from ML classifier for predicted class before season adjustment.

2. Calendar suitability
- Seasonal score from local calendar source.

3. Adjusted confidence
- `raw_model_confidence * (calendar_suitability + eps)`
- Used for final ranking and risk handling.

`eps` prevents hard-zero collapse when suitability is near zero while still penalizing out-of-season crops.

## 8. Curves and Explanation Artifacts

### 8.1 Model curves (`curves`)
- Generated by model API from model probabilities.
- Includes `topk_confidence`.

### 8.2 Agent curves (`llm_curves`)
Grounded, backend-derived only:
- `decision_stages`: raw -> rerank -> final
- `topk_confidence`: top-k labels and values
- `shap_cumulative`: cumulative absolute SHAP contribution order

No curve is generated from LLM reasoning.

## 9. XAI Evaluation Pipeline

Script: `xai_eval/evaluate.py`

Outputs:
- `xai_eval/report.json`
- `xai_eval/calibration_report.json`
- legacy compatibility file: `xai_eval/evaluation_report.json`

Metrics:
1. SHAP faithfulness
- Deletion AUC by masking features in descending `|SHAP|` order.

2. LIME faithfulness
- Deletion AUC by masking features in descending `|LIME weight|` order.

3. LIME local fidelity
- `R^2` between LIME surrogate and black-box probabilities.

4. Stability
- Input perturbation tests
- Top-k feature overlap (Jaccard)
- Rank correlation (Spearman)

5. Calibration
- Bin-based confidence vs empirical accuracy
- Expected Calibration Error (ECE)

Runtime access:
- `GET /metrics/xai` returns cached evaluation and calibration reports.

## 10. Reliability and Failure Handling

1. LLM provider failures
- Handles 4xx/5xx/timeouts/rate limits via fallback template.
- Keeps API contract stable for demos.

2. External data gaps
- Missing pH from SoilGrids uses controlled fallback with explicit warning.
- Weather/soil values are marked as estimated.

3. Strict validation
- Prevents unsupported output formats and hidden reasoning leakage.

4. Test coverage
- `testing/test_system_extensive.py`
- `testing/test_tool_routing_suite.py`
- `testing/test_agent_pipeline.py`
- prompt suite execution with quality report artifacts.

## 11. Security and Configuration

Configuration loaded from `.env` via `core/config.py`.

Supported LLM modes:
- `LLM_PROVIDER=local`
- `LLM_PROVIDER=openrouter`
- `LLM_PROVIDER=openai`

Guidelines:
- Never hardcode keys in source.
- Keep `.env` out of version control.
- Use `.env.example` as template.

## 12. Files of Interest

- `api/main.py`: orchestration, reranking, LLM gating, fallback, `/metrics/xai`
- `api/prompts.py`: system/user prompt templates
- `api/schemas.py`: request/response contract
- `services/*.py`: external provider adapters
- `model_service/predict_xai_client.py`: model API client
- `xai_eval/evaluate.py`: offline evaluation pipeline
- `scripts/run_prompt_suite.py`: prompt QA harness
- `testing/*.py`: test suites

## 13. Design Rationale (Short)

- Separate model scoring from agent orchestration for maintainability.
- Keep agronomy-critical features (`N/P/K`) mandatory and non-fabricated.
- Make seasonality explicit through reranking instead of hidden post-processing.
- Keep LLM advisory non-authoritative; structured outputs remain source of truth.
- Build observability into responses (warnings, provenance, tool_calls, confidence decomposition).
