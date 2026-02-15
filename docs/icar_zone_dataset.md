# ICAR/OGD RAG Zone Dataset: Creation Report

## Purpose
This dataset is used by the ICAR RAG reranker in the Agent API. It supports location-aware reranking with full row-level provenance fields (`source_name`, `source_ref`, `data_quality`).

## Important scope note
- This is a **compiled zone-memory dataset for prototype/research use**.
- District rows are created by joining:
  1. district localization records, and
  2. crop-season claim rows sourced from official India agriculture portals.
- Therefore, district-level agronomy rows are tagged `data_quality=incomplete` unless a source explicitly provides district-level agronomy statements.

## Source files (downloaded / archived locally)
1. OGD catalog metadata (ICAR agro-ecological zoning)
- URL: `https://www.data.gov.in/catalog/agro-ecological-zoning`
- Backend JSON: `https://www.data.gov.in/backend/dms/v2/catalog/agro-ecological-zoning?_format=json`
- Local archive: `data/sources/raw/icar_agro_ecological_catalog.json`, `data/sources/raw/icar_agro_ecological_page.html`

2. OGD catalog metadata (district/season/crop production, DES)
- URL: `https://www.data.gov.in/catalog/district-wise-season-wise-crop-production-statistics-0`
- Backend JSON: `https://www.data.gov.in/backend/dms/v2/catalog/district-wise-season-wise-crop-production-statistics-0?_format=json`
- Local archive: `data/sources/raw/des_crop_production_catalog.json`, `data/sources/raw/des_crop_production_resource.html`

3. District localization source
- URL: `https://www.data.gov.in/catalog/local-government-directory-lgd`
- Local file used by pipeline: `data/sources/India-State-District.json`

4. Crop package references (Govt portal)
- Portal: Vikaspedia (MeitY/C-DAC)
- Example URL: `https://en.vikaspedia.in/agriculture/crop-production/package-of-practices/cereals-1/rice`
- Row-level references stored in: `data/sources/icar_crop_memory_notes.csv`

## Build workflow
1. Download and archive official source pages/metadata:
```bash
uv run python scripts/download_official_sources.py
```
2. Build dataset CSVs:
```bash
uv run python scripts/build_icar_dataset.py
```
3. Validate schema/provenance/size:
```bash
uv run python scripts/validate_icar_dataset.py
```
4. Build RAG corpus documents from exploded rows:
```bash
uv run python scripts/build_icar_rag_corpus.py
```

## CSV outputs
1. `data/icar_agro_zones_india.csv`
- State-season summaries used for observability.

2. `data/icar_agro_zones_india_exploded.csv`
- Primary ingestion file used by reranker.
- Required fields include:
  - location: `state`, `district`
  - agronomy token fields: `season`, `crop`, `suitability`, `key_risks`
  - provenance: `source_name`, `source_ref`, `data_quality`

## RAG document format
Each row is converted to tokenized markdown under `rag_corpus/icar_zones/`:
- `ZONE_ID`, `ZONE_NAME`, `STATE`, `DISTRICT`, `SEASON`, `CROP`, `SUITABILITY`
- `RISK`, `SOIL`, `CLIMATE`, `SOURCE_NAME`, `SOURCE_REF`, `EVIDENCE`

## Reranker semantics
The reranker computes per-crop suitability and adjusted confidence with deterministic rules:
- base score from `SUITABILITY` token
- location match quality (district/state/latlon/unknown)
- risk penalty rules from explicit `RISK` token

## Known limitations
- Some official source endpoints (for full historical crop files) may be intermittently unavailable at fetch time.
- District rows currently represent localization expansion over sourced crop-season claims; they are not direct district-level agronomy statements unless explicit source evidence exists.
- These rows are therefore marked `data_quality=incomplete` by design.
