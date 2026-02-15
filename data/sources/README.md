# Source Bundle for ICAR RAG Zone-Memory Dataset

This directory stores local source artifacts and row-level claim tables used to generate:
- `data/icar_agro_zones_india.csv`
- `data/icar_agro_zones_india_exploded.csv`

## Files
- `India-State-District.json`: district localization reference (LGD/data.gov source chain)
- `icar_crop_memory_notes.csv`: crop-season claim rows with explicit `source_name` and `source_ref`
- `raw/*.json|*.html`: archived official pages/metadata fetched by `scripts/download_official_sources.py`
- `official_source_registry.json`: fetch log and statuses

## Provenance policy
- Every exploded row must contain non-empty `source_name` and `source_ref`.
- If district-level agronomy evidence is not explicit in source documents, rows are marked `data_quality=incomplete`.

## Regeneration
```bash
uv run python scripts/download_official_sources.py
uv run python scripts/build_icar_dataset.py
uv run python scripts/validate_icar_dataset.py
uv run python scripts/build_icar_rag_corpus.py
```
