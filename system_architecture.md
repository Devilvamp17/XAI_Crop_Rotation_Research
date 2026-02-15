# System Architecture

This document describes the current architecture after replacing crop-calendar reranking with an ICAR RAG-memory reranker.

## 1) Top-Level Design

1. Model API (`main.py`, port `8000`)
- Trained models (`xgboost`, `random_forest`, `logistic_regression`)
- SHAP + LIME + top-k confidence outputs

2. Agent API (`api/main.py`, port `8100`)
- Feature validation and enrichment (geocode/weather/soil)
- ICAR RAG reranking
- Confidence decomposition and warnings
- LLM advisory + strict validation + fallback
- Run archiving

3. Local RAG + Data Layer
- `data/icar_agro_zones_india_exploded.csv` (primary rerank memory)
- `rag_corpus/icar_zones/*.md` tokenized docs
- `services/rag.py` TF-IDF retrieval (local)
- `services/icar_rag_reranker.py` deterministic scoring

4. Offline evaluation
- `xai_eval/evaluate.py`
- `GET /metrics/xai`, `GET /metrics/xai_curves`

## 2) Data Flow

```text
Client
  -> Agent API (/recommend or /recommend_with_llm)
      -> Validate N/P/K (mandatory)
      -> Optional enrich from geocode/weather/soil
      -> Model API /predict
      -> ICAR RAG reranker (district/state/latlon/unknown)
      -> Confidence decomposition
      -> Optional LLM response generation + validation/fallback
      -> Archive outputs
      -> Response
```

## 3) ICAR Reranking

Reranker behavior:
- Resolve zone by priority: district > state > lat/lon > unknown
- Retrieve supporting memory docs from `rag_corpus/icar_zones`
- Parse strict tokens from retrieved snippets:
  - `ZONE_ID`, `STATE`, `DISTRICT`, `SEASON`, `CROP`, `SUITABILITY`, `RISK`, `SOURCE_*`
- Compute per-crop `rag_suitability` deterministically
- Add XAI-aware signals from top SHAP features:
  - query expansion using feature keywords
  - small deterministic boost when retrieved evidence matches top SHAP feature context
- Re-rank top-k by adjusted confidence

Conflict handling:
- If top-1 changes after rerank, emit `rerank_conflict`
- Add warning for coarse localization and low confidence

## 4) Confidence Semantics

```text
adjusted_confidence = raw_model_confidence
                    * (rag_suitability + eps)
                    * data_quality_factor
                    * disagreement_multiplier
```

Aliases retained for backward compatibility (deprecated):
- `calendar_suitability = rag_suitability`
- `calendar_conflict = rerank_conflict`

## 5) Dataset + Corpus Pipeline

Source-first build pipeline:
1. `scripts/download_official_sources.py` archives official OGD/ICAR metadata under `data/sources/raw/`.
2. `scripts/build_icar_dataset.py` builds base + exploded CSVs from sourced claim rows (`data/sources/icar_crop_memory_notes.csv`) and district localization records.
3. `scripts/validate_icar_dataset.py` enforces schema, provenance fields, and size constraints.
4. `scripts/build_icar_rag_corpus.py` converts exploded rows to tokenized docs under `rag_corpus/icar_zones/`.

Detailed provenance and limitations are documented in `docs/icar_zone_dataset.md`.

Outputs:
- `data/icar_agro_zones_india.csv`
- `data/icar_agro_zones_india_exploded.csv`
- `rag_corpus/icar_zones/*.md`

## 6) Archiving

Each `/recommend_with_llm` request archives:
- `request.json`
- `prompts.json`
- `tool_calls.json`
- `recommendation.json`
- `validation.json`
- `llm_rounds.json`
- `llm_response.txt`
- `rag_hits.json`
- `icar_zone_match.json`
- `rag_rerank.json`

## 7) Reliability and Safety

- Never fabricates N/P/K.
- External enrichment values are flagged in provenance.
- Reranker is deterministic and local.
- LLM output is validated; fallback template preserves API reliability.

## 8) Prompt and Evaluation Pipeline

Prompt suites:
- `scripts/run_prompt_suites_full.py` runs `main`, `rag_live`, and `run2` prompt packs.
- `scripts/run_prompt_suite.py --prompts prompts/llm_prompt_suite_refresh.json` runs the refreshed prompt set.

Suite and prompt outputs:
- `artifacts/llm_prompt_outputs_main.json`
- `artifacts/llm_prompt_outputs_rag_live.json`
- `artifacts/llm_prompt_outputs_run2.json`
- `artifacts/llm_prompt_outputs_refresh.json`

## 9) Evaluation + Health

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

Evaluation tables/plots are generated under:
- `evaluation/out/<run_id>/`
