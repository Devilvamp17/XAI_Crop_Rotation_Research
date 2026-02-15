# LLM Prompt Test Outputs

Generated: 2026-02-15T10:54:46.375517Z
Model API: `http://127.0.0.1:8000`
Agent API: `http://127.0.0.1:8100`

## p01_standard_summary

**Prompt**

> Give a standard recommendation summary.

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `0.40959656387567517`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing raw/adjusted confidence terms; round2: Missing required sections']`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Jute is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.9638
Season-adjusted confidence: 0.4096 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
jute (raw=0.9638, suit=0.38, adj=0.4096); rice (raw=0.0030, suit=0.38, adj=0.0013); maize (raw=0.0027, suit=0.38, adj=0.0011)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## p02_farmer_simple

**Prompt**

> Explain this for a small farmer in very simple language with 3 clear action steps.

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `0.40959656387567517`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Action checklist must contain exactly 3 bullet points; round2: Missing required sections']`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Jute is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.9638
Season-adjusted confidence: 0.4096 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
jute (raw=0.9638, suit=0.38, adj=0.4096); rice (raw=0.0030, suit=0.38, adj=0.0013); maize (raw=0.0027, suit=0.38, adj=0.0011)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## p03_risk_uncertainty

**Prompt**

> Focus on risk and uncertainty. When should I avoid planting the top crop?

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `0.40959656387567517`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing raw/adjusted confidence terms; round2: Contains internal reasoning leak']`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Jute is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.9638
Season-adjusted confidence: 0.4096 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
jute (raw=0.9638, suit=0.38, adj=0.4096); rice (raw=0.0030, suit=0.38, adj=0.0013); maize (raw=0.0027, suit=0.38, adj=0.0011)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## p04_tradeoff_shap

**Prompt**

> Compare tradeoffs among top 3 crops and mention strongest SHAP signals briefly.

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `0.40959656387567517`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Action checklist must contain exactly 3 bullet points; round2: Contains internal reasoning leak']`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Jute is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.9638
Season-adjusted confidence: 0.4096 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
jute (raw=0.9638, suit=0.38, adj=0.4096); rice (raw=0.0030, suit=0.38, adj=0.0013); maize (raw=0.0027, suit=0.38, adj=0.0011)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## p05_location_enrichment

**Prompt**

> Use location enrichment for Delhi and explain confidence limits.

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `0.17794377330690622`
- Warnings: `['Weather values are estimated from Open-Meteo current conditions.', 'SoilGrids pH unavailable at this point; using fallback pH=6.5.', 'Soil values are estimated from SoilGrids.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing required sections; round2: Action checklist must contain exactly 3 bullet points']`
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

## p06_no_tool_false_prompt

**Prompt**

> Just greet me and do not call any external tools. Keep it one line.

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `1.0119444519281389`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'LLM fallback applied: validation_failed: Contains internal reasoning leak; round2: Missing required sections']`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Jute is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.9638
Season-adjusted confidence: 1.0119 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
jute (raw=0.9638, suit=1.00, adj=1.0119); rice (raw=0.0030, suit=1.00, adj=0.0032); maize (raw=0.0027, suit=1.00, adj=0.0028)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
No high-risk warning: adjusted confidence is at or above threshold.
```

## p07_missing_npk_should_fail

**Prompt**

> I only know location, please decide crop for me.

- Expected HTTP: `400`
- Status: `PASSED (expected non-200)`
- HTTP: `400`
- Response: `{'detail': {'message': 'Missing required N/P/K values. Cannot fabricate these features.', 'missing_features': ['N'], 'hint': 'Provide soil test values for N, P, K.'}}`
- Quality Score: `100` (required_hits=0, bullets=0, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
N/A (expected non-200 case)
```

## p08_low_confidence_action

**Prompt**

> If confidence is low, give me a conservative plan.

- Expected HTTP: `200`
- Final Crop: `maize`
- Confidence: `0.32503478296101096`
- Warnings: `['Weather values are estimated from Open-Meteo current conditions.', 'SoilGrids pH unavailable at this point; using fallback pH=6.5.', 'Soil values are estimated from SoilGrids.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', "LLM fallback applied: Client error '400 Bad Request' for url 'https://openrouter.ai/api/v1/chat/completions'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400"]`
- Inferred Tools Used: `['geocode_location', 'get_soil_properties', 'get_weather']`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Maize is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.9270
Season-adjusted confidence: 0.3250 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
maize (raw=0.9270, suit=0.50, adj=0.3250); kidneybeans (raw=0.0231, suit=0.50, adj=0.0081); mothbeans (raw=0.0163, suit=0.50, adj=0.0057)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## p09_technical_xai

**Prompt**

> Give a technical explanation with SHAP and LIME details for an agronomy researcher.

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

## p10_irrelevant_prompt

**Prompt**

> Write a haiku about farming but still include recommendation and confidence.

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `0.40959656387567517`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', "LLM fallback applied: Client error '402 Payment Required' for url 'https://openrouter.ai/api/v1/chat/completions'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/402"]`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Jute is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.9638
Season-adjusted confidence: 0.4096 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
jute (raw=0.9638, suit=0.38, adj=0.4096); rice (raw=0.0030, suit=0.38, adj=0.0013); maize (raw=0.0027, suit=0.38, adj=0.0011)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## p11_calendar_conflict_explain

**Prompt**

> If calendar changes top crop, explain conflict clearly and suggest fallback.

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `0.17794377330690622`
- Warnings: `['Weather values are estimated from Open-Meteo current conditions.', 'SoilGrids pH unavailable at this point; using fallback pH=6.5.', 'Soil values are estimated from SoilGrids.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Contains internal reasoning leak; round2: Contains internal reasoning leak']`
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

## p12_input_validation_question

**Prompt**

> Tell me what extra field data I should collect before planting.

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

## p13_market_angle

**Prompt**

> Add a brief note on market-risk uncertainty while keeping agronomy first.

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `0.1077910193428397`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Contains internal reasoning leak; round2: Missing required sections']`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Jute is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.2984
Season-adjusted confidence: 0.1078 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
jute (raw=0.2984, suit=0.38, adj=0.1078); rice (raw=0.0492, suit=0.38, adj=0.0178); mungbean (raw=0.0400, suit=0.38, adj=0.0145)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```
