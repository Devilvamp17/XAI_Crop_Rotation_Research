# LLM-Integrated Crop Recommendation + XAI

Production-style crop recommendation stack with:
- ML inference (`xgboost`, `random_forest`, `logistic_regression`)
- Per-instance SHAP + LIME explanations
- Season-aware calendar re-ranking
- LLM advisory layer with strict output contract and fallback
- Offline XAI evaluation (faithfulness, fidelity, stability, calibration)

## Repository Structure
```text
.
├── api/                    # Agent/orchestration API (port 8100)
├── core/                   # Configuration loader (.env)
├── model_service/          # Client for model API (port 8000)
├── services/               # External service adapters (geocode/weather/soil/calendar/LLM)
├── scripts/                # Prompt suite + setup scripts
├── prompts/                # Prompt and routing test suites
├── testing/                # Automated tests
├── xai_eval/               # Evaluation pipeline + generated reports
├── models/                 # Trained model artifacts
├── xai/                    # Precomputed explainers
├── results/                # Visual outputs
├── main.py                 # Model API
├── stream.py               # Streamlit app
└── system_architecture.md  # Detailed architecture documentation
```

## Core Capabilities
- Predict top-k crops from: `N, P, K, temperature, humidity, ph`
- Return explanation artifacts:
  - `shap` contributions
  - `lime` local explanation
  - `curves.topk_confidence`
- Enrich missing environmental data from free APIs when location is provided
- Re-rank model outputs with crop calendar suitability:
  - `adjusted_confidence = raw_model_confidence * (calendar_suitability + eps)`
- Return provenance for each feature (`user`, `weather_api`, `soil_api`, fallback)
- Provide LLM-generated advisory in strict 5-section format
- Fallback to deterministic template response when LLM fails or violates output rules

## APIs

### 1) Model API (`main.py`, port `8000`)
Run:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Endpoints:
- `GET /health`
- `POST /predict`

Example:
```bash
curl --json '{
  "N": 90,
  "P": 42,
  "K": 43,
  "temperature": 25.6,
  "humidity": 71.4,
  "ph": 6.4
}' http://127.0.0.1:8000/predict
```

### 2) Agent API (`api/main.py`, port `8100`)
Run:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8100
```

Endpoints:
- `GET /health`
- `GET /tools`
- `GET /llm/health`
- `GET /metrics/xai`
- `POST /recommend`
- `POST /recommend_with_llm`

Example (`/recommend_with_llm`):
```bash
curl --json '{
  "query": "Which crop should I plant and why?",
  "recommendation_input": {
    "location": "Delhi, India",
    "N": 90,
    "P": 42,
    "K": 43,
    "top_k": 3
  }
}' http://127.0.0.1:8100/recommend_with_llm
```

## Tool Routing Rules Implemented
- If prompt says no tools (`do not call/use tools`, etc.) -> no external tools are called
- If all required features are provided -> no geocode/weather/soil calls
- If `N/P/K` missing -> returns `400` (never fabricated)
- If location is provided and `temperature/humidity` missing -> weather API call
- If location is provided and `ph` missing -> soil API call

## Response Additions (Agent)
`POST /recommend` and `/recommend_with_llm` include:
- `raw_model_confidence`
- `calendar_suitability`
- `adjusted_confidence`
- `eps`
- `llm_curves`:
  - `decision_stages`
  - `topk_confidence`
  - `shap_cumulative`
- `provenance`
- `tool_calls`
- `warnings`

## LLM Providers and Fallback
Configurable provider via `.env`:
- `LLM_PROVIDER=local|openrouter|openai`

Behavior:
- Calls provider for advisory text
- Validates output contract (no CoT leaks, strict 5 sections, confidence terms, checklist bullets)
- If provider fails (e.g. 402/429/timeout) or output is invalid -> template fallback response is returned

## Environment Variables
Copy `.env.example` to `.env` and set values.

Important keys:
- `MODEL_API_BASE_URL`
- `NOMINATIM_URL`, `NOMINATIM_USER_AGENT`
- `OPEN_METEO_URL`
- `SOILGRIDS_URL`
- `LLM_PROVIDER`
- `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL`
- `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`
- `OPENAI_API_KEY`, `OPENAI_MODEL`

## Testing
Run core tests:
```bash
uv run python testing/test_system_extensive.py
uv run python testing/test_tool_routing_suite.py
uv run python testing/test_agent_pipeline.py
```

Prompt suite:
```bash
uv run python scripts/run_prompt_suite.py
```
Outputs:
- `artifacts/llm_prompt_outputs.json`
- `artifacts/llm_prompt_outputs.md`

## XAI Evaluation Pipeline
Run:
```bash
uv run python xai_eval/evaluate.py
```
Generated:
- `xai_eval/report.json`
- `xai_eval/evaluation_report.json` (legacy compatibility)
- `xai_eval/calibration_report.json`

Metrics include:
- SHAP faithfulness (`deletion_auc`)
- LIME faithfulness (`deletion_auc`)
- LIME local fidelity (`fidelity_r2`)
- Stability (`avg_overlap`, `avg_rank_corr`)

## Streamlit
Run:
```bash
streamlit run stream.py
```

## Notes
- Do not commit real API keys.
- Keep `.env` local.
- Free API services can rate-limit; caching is enabled for geocode/soil flows.
- For full architecture details, see `system_architecture.md`.
