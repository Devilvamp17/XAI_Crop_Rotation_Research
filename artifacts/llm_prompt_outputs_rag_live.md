# LLM Prompt Test Outputs

Generated: 2026-02-15T10:58:30.678878Z
Model API: `http://127.0.0.1:8000`
Agent API: `http://127.0.0.1:8100`

## rag01_delhi_explain

**Prompt**

> Use location enrichment for Delhi and explain why this crop fits current season.

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `0.17794377330690622`
- Warnings: `['Weather values are estimated from Open-Meteo current conditions.', 'SoilGrids pH unavailable at this point; using fallback pH=6.5.', 'Soil values are estimated from SoilGrids.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', "LLM fallback applied: Client error '402 Payment Required' for url 'https://openrouter.ai/api/v1/chat/completions'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/402"]`
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

## rag02_mumbai_uncertainty

**Prompt**

> For Mumbai, explain recommendation with uncertainty and practical checks.

- Expected HTTP: `200`
- Final Crop: `coffee`
- Confidence: `0.19640469510108233`
- Warnings: `['Weather values are estimated from Open-Meteo current conditions.', 'SoilGrids pH unavailable at this point; using fallback pH=6.5.', 'Soil values are estimated from SoilGrids.', 'Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing raw/adjusted confidence terms; round2: Contains internal reasoning leak']`
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

## rag03_conflict_required

**Prompt**

> If calendar changes top crop, explain that conflict clearly.

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `0.17794377330690622`
- Warnings: `['Weather values are estimated from Open-Meteo current conditions.', 'SoilGrids pH unavailable at this point; using fallback pH=6.5.', 'Soil values are estimated from SoilGrids.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing raw/adjusted confidence terms; round2: Missing raw/adjusted confidence terms']`
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

## rag04_farmer_simple

**Prompt**

> Explain in simple farmer language and give exactly 3 action steps.

- Expected HTTP: `200`
- Final Crop: `maize`
- Confidence: `0.3482826334238052`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing raw/adjusted confidence terms; round2: Missing raw/adjusted confidence terms']`
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

## rag05_technical_xai

**Prompt**

> Give technical SHAP/LIME explanation suitable for an agronomy researcher.

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `0.08659769868478177`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing raw/adjusted confidence terms; round2: Contains internal reasoning leak']`
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

## rag06_no_tools

**Prompt**

> Do not use any external tools. Provide concise recommendation.

- Expected HTTP: `200`
- Final Crop: `coffee`
- Confidence: `0.7683316384255886`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'LLM fallback applied: validation_failed: Contains internal reasoning leak; round2: Missing raw/adjusted confidence terms']`
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

## rag07_missing_npk

**Prompt**

> I only know location, decide crop.

- Expected HTTP: `400`
- Status: `PASSED (expected non-200)`
- HTTP: `400`
- Response: `{'detail': {'message': 'Missing required N/P/K values. Cannot fabricate these features.', 'missing_features': ['N'], 'hint': 'Provide soil test values for N, P, K.'}}`
- Quality Score: `100` (required_hits=0, bullets=0, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
N/A (expected non-200 case)
```

## rag08_risk_plan

**Prompt**

> If confidence is low, provide a conservative plan.

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

## rag09_rice_case

**Prompt**

> Recommend for this direct input and include raw vs adjusted confidence.

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `0.2127870112657547`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing raw/adjusted confidence terms; round2: Contains internal reasoning leak']`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Jute is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.5890
Season-adjusted confidence: 0.2128 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
jute (raw=0.5890, suit=0.38, adj=0.2128); rice (raw=0.0291, suit=0.38, adj=0.0105); mungbean (raw=0.0235, suit=0.38, adj=0.0085)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## rag10_maize_case

**Prompt**

> Give recommendation and mention strongest feature signal from SHAP.

- Expected HTTP: `200`
- Final Crop: `maize`
- Confidence: `0.3391794960945845`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing raw/adjusted confidence terms; round2: Contains internal reasoning leak']`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Maize is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.9389
Season-adjusted confidence: 0.3392 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
maize (raw=0.9389, suit=0.38, adj=0.3392); mothbeans (raw=0.0185, suit=0.38, adj=0.0067); pomegranate (raw=0.0036, suit=0.38, adj=0.0013)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## rag11_high_uncertain_location

**Prompt**

> Use location enrichment for Jaipur and focus on uncertainty limits.

- Expected HTTP: `200`
- Final Crop: `coffee`
- Confidence: `0.1964731609672308`
- Warnings: `['Weather values are estimated from Open-Meteo current conditions.', 'SoilGrids pH unavailable at this point; using fallback pH=6.5.', 'Soil values are estimated from SoilGrids.', 'Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing raw/adjusted confidence terms; round2: Missing raw/adjusted confidence terms']`
- Inferred Tools Used: `['geocode_location', 'get_soil_properties', 'get_weather']`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Coffee is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.6043
Season-adjusted confidence: 0.1965 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
coffee (raw=0.6043, suit=0.46, adj=0.1965); chickpea (raw=0.3564, suit=0.78, adj=0.1890); mango (raw=0.0283, suit=0.46, adj=0.0092)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## rag12_compare_tradeoff

**Prompt**

> Compare top 3 crops and explain tradeoff between probability and season fit.

- Expected HTTP: `200`
- Final Crop: `coffee`
- Confidence: `0.2539799194037914`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', "LLM fallback applied: Client error '402 Payment Required' for url 'https://openrouter.ai/api/v1/chat/completions'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/402"]`
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
