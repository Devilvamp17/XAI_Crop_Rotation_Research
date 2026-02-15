# LLM Prompt Test Outputs

Generated: 2026-02-15T11:01:36.046410Z
Model API: `http://127.0.0.1:8000`
Agent API: `http://127.0.0.1:8100`

## r2_p01_standard

**Prompt**

> Give the recommendation in the strict 5-section format.

- Expected HTTP: `200`
- Final Crop: `coffee`
- Confidence: `0.2539799194037914`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing raw/adjusted confidence terms; round2: Contains internal reasoning leak']`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Coffee is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.7031
Season-adjusted confidence: 0.2540 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
coffee (raw=0.7031, suit=0.38, adj=0.2540); jute (raw=0.2828, suit=0.38, adj=0.1022); blackgram (raw=0.0025, suit=0.38, adj=0.0009)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## r2_p02_location_india

**Prompt**

> Use location enrichment for Mumbai and explain uncertainty clearly.

- Expected HTTP: `200`
- Final Crop: `coffee`
- Confidence: `0.19640469510108233`
- Warnings: `['Weather values are estimated from Open-Meteo current conditions.', 'SoilGrids pH unavailable at this point; using fallback pH=6.5.', 'Soil values are estimated from SoilGrids.', 'Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing raw/adjusted confidence terms; round2: Missing raw/adjusted confidence terms']`
- Inferred Tools Used: `['geocode_location', 'get_soil_properties', 'get_weather']`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Coffee is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.6041
Season-adjusted confidence: 0.1964 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
coffee (raw=0.6041, suit=0.46, adj=0.1964); jute (raw=0.2431, suit=0.46, adj=0.0790); blackgram (raw=0.0264, suit=0.46, adj=0.0086)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## r2_p03_calendar_conflict

**Prompt**

> If calendar changes top crop, explain why and suggest fallback.

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `0.17794377330690622`
- Warnings: `['Weather values are estimated from Open-Meteo current conditions.', 'SoilGrids pH unavailable at this point; using fallback pH=6.5.', 'Soil values are estimated from SoilGrids.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Contains internal reasoning leak; round2: Missing raw/adjusted confidence terms']`
- Inferred Tools Used: `['geocode_location', 'get_soil_properties', 'get_weather']`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Jute is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.5075
Season-adjusted confidence: 0.1779 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
jute (raw=0.5075, suit=0.50, adj=0.1779); coffee (raw=0.3906, suit=0.50, adj=0.1369); kidneybeans (raw=0.0115, suit=0.50, adj=0.0040)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## r2_p04_farmer_style

**Prompt**

> Explain for a small farmer with simple language and exactly 3 action bullets.

- Expected HTTP: `200`
- Final Crop: `maize`
- Confidence: `0.3482826334238052`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', "LLM fallback applied: Client error '402 Payment Required' for url 'https://openrouter.ai/api/v1/chat/completions'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/402"]`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Maize is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.9641
Season-adjusted confidence: 0.3483 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
maize (raw=0.9641, suit=0.38, adj=0.3483); mothbeans (raw=0.0093, suit=0.38, adj=0.0034); blackgram (raw=0.0023, suit=0.38, adj=0.0008)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## r2_p05_no_tools

**Prompt**

> Do not use any external tools. Give concise recommendation.

- Expected HTTP: `200`
- Final Crop: `coffee`
- Confidence: `0.7683316384255886`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'LLM fallback applied: validation_failed: Missing raw/adjusted confidence terms; round2: Missing raw/adjusted confidence terms']`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Coffee is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.8609
Season-adjusted confidence: 0.7683 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
coffee (raw=0.8609, suit=1.00, adj=0.7683); jute (raw=0.1247, suit=1.00, adj=0.1113); rice (raw=0.0012, suit=1.00, adj=0.0010)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
No high-risk warning: adjusted confidence is at or above threshold.
```

## r2_p06_missing_npk_fail

**Prompt**

> I only know location, please decide the crop.

- Expected HTTP: `400`
- Status: `PASSED (expected non-200)`
- HTTP: `400`
- Response: `{'detail': {'message': 'Missing required N/P/K values. Cannot fabricate these features.', 'missing_features': ['N'], 'hint': 'Provide soil test values for N, P, K.'}}`
- Quality Score: `100` (required_hits=0, bullets=0, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
N/A (expected non-200 case)
```

## r2_p07_technical_xai

**Prompt**

> Give a technical SHAP/LIME-focused summary for an agronomy researcher.

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `0.08659769868478177`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing raw/adjusted confidence terms; round2: Missing raw/adjusted confidence terms']`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Jute is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.2397
Season-adjusted confidence: 0.0866 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
jute (raw=0.2397, suit=0.38, adj=0.0866); cotton (raw=0.0659, suit=0.38, adj=0.0238); blackgram (raw=0.0654, suit=0.38, adj=0.0236)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## r2_p08_conservative

**Prompt**

> If confidence is below 0.6, provide a conservative plan with risk warning.

- Expected HTTP: `200`
- Final Crop: `maize`
- Confidence: `0.297815336085856`
- Warnings: `['Weather values are estimated from Open-Meteo current conditions.', 'SoilGrids pH unavailable at this point; using fallback pH=6.5.', 'Soil values are estimated from SoilGrids.', 'Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Contains internal reasoning leak; round2: Missing required sections']`
- Inferred Tools Used: `['geocode_location', 'get_soil_properties', 'get_weather']`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Maize is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.9160
Season-adjusted confidence: 0.2978 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
maize (raw=0.9160, suit=0.46, adj=0.2978); mango (raw=0.0427, suit=0.46, adj=0.0139); mothbeans (raw=0.0161, suit=0.46, adj=0.0052)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```
