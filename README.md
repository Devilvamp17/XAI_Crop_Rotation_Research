# LLM-Integrated Crop Recommendation + ICAR RAG Reranker

Two-API crop recommendation stack with deterministic reranking and explainability:
- Model API (`main.py`, port `8000`): ML + SHAP + LIME
- Agent API (`api/main.py`, port `8100`): feature enrichment + ICAR RAG rerank + LLM advisory + archiving

## What Changed
The previous crop-calendar reranking logic has been replaced by an **ICAR/NBSS&LUP-inspired RAG-memory reranker** backed by local CSV + local TF-IDF corpus.

## Repository Structure
```text
.
├── api/
├── core/
├── services/
├── data/
│   ├── sources/
│   ├── icar_agro_zones_india.csv
│   └── icar_agro_zones_india_exploded.csv
├── rag_corpus/
│   └── icar_zones/
├── scripts/
├── testing/
├── xai_eval/
├── artifacts/
├── docs/
│   └── icar_zone_dataset.md
├── main.py
└── system_architecture.md
```

## ICAR RAG Reranker
Reranker inputs:
- model top-k (`crop`, `raw_model_confidence`)
- resolved location context (district/state/lat-lon/unknown)
- season derived from month

Scoring:
- `rag_suitability` from retrieved tokenized docs (`SUITABILITY:HIGH|MED|LOW`)
- deterministic penalties for explicit risks
- match-quality factor by localization strength
- XAI-aware adjustment from top SHAP features (query expansion + feature-token match boost)

Final confidence:
```text
adjusted_confidence = raw_model_confidence * (rag_suitability + eps) * data_quality_factor * disagreement_multiplier
```

Rerank metadata now includes:
- `rag_rerank.xai_rag_reasoning.top_shap_features`
- `rag_rerank.xai_rag_reasoning.per_crop[*].matched_features`

Backward-compatible aliases (deprecated):
- `calendar_suitability` -> `rag_suitability`
- `calendar_conflict` -> `rerank_conflict`

## Build Dataset + Corpus
```bash
uv run python scripts/build_icar_dataset.py
uv run python scripts/validate_icar_dataset.py
uv run python scripts/build_icar_rag_corpus.py
```

## APIs
Run Model API:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Run Agent API:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8100
```

Agent endpoints:
- `GET /health`
- `GET /tools`
- `GET /llm/health`
- `GET /rag/health`
- `POST /rag/search`
- `GET /metrics/xai`
- `GET /metrics/xai_curves`
- `POST /recommend`
- `POST /recommend_with_llm`

## Prompt Suites
Run standard suites:
```bash
uv run python scripts/run_prompt_suites_full.py
```

Run refreshed prompts (new cases):
```bash
uv run python scripts/run_prompt_suite.py \
  --prompts prompts/llm_prompt_suite_refresh.json \
  --out-json artifacts/llm_prompt_outputs_refresh.json \
  --out-md artifacts/llm_prompt_outputs_refresh.md
```

## Archiving
Per `/recommend_with_llm` run:
```text
artifacts/runs/<timestamp>__<request_id>/
  request.json
  prompts.json
  tool_calls.json
  recommendation.json
  validation.json
  llm_rounds.json
  llm_response.txt
  rag_hits.json
  icar_zone_match.json
  rag_rerank.json
```

## Testing
```bash
uv run python testing/test_icar_reranker.py
uv run python testing/test_system_extensive.py
uv run python testing/test_pipeline_improvements.py
```

## Notes
- Runtime reranking is fully local/offline.
- Source/provenance fields are mandatory in dataset rows.
- See `docs/icar_zone_dataset.md` for schema, sources, and limitations.


## Evaluation + Health

Run combined offline evaluation, RAG rerank checks, unit checks, and API health checks:

```bash
uv run python scripts/run_system_evaluation.py
```

Outputs are written to `artifacts/reports/`:
- `combined_pipeline_evaluation.json`
- `combined_pipeline_evaluation.md`
- `rag_rerank_evaluation.json`
- `rag_rerank_evaluation.md`
- `health_check.json`
- `prompt_suite_execution_summary.json`
- `prompt_suite_execution_summary.md`
- `prompt_suite_refresh_summary.json`
- `prompt_suite_refresh_summary.md`
- `rag_artifact_consistency_audit.json`
- `rag_artifact_consistency_audit.md`

Evaluation outputs are written under:
- `evaluation/out/<run_id>/`


## Official Source Refresh
To refresh official source snapshots and rebuild the ICAR RAG dataset/corpus:
```bash
uv run python scripts/download_official_sources.py
uv run python scripts/build_icar_dataset.py
uv run python scripts/validate_icar_dataset.py
uv run python scripts/build_icar_rag_corpus.py
```
See `docs/icar_zone_dataset.md` for source list, schema, and limitations.
