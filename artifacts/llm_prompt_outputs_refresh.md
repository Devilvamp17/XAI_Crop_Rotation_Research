# LLM Prompt Test Outputs

Generated: 2026-02-15T10:47:41.926165Z
Model API: `http://127.0.0.1:8000`
Agent API: `http://127.0.0.1:8100`

## r3_p01_baseline_summary

**Prompt**

> Give a concise agronomy-first recommendation summary.

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `0.17081102088093755`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing raw/adjusted confidence terms; round2: Missing required sections']`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Jute is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.4728
Season-adjusted confidence: 0.1708 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
jute (raw=0.4728, suit=0.38, adj=0.1708); coffee (raw=0.4246, suit=0.38, adj=0.1534); blackgram (raw=0.0183, suit=0.38, adj=0.0066)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## r3_p02_farmer_three_steps

**Prompt**

> Explain for a small farmer with exactly three practical action steps.

- Expected HTTP: `200`
- Final Crop: `maize`
- Confidence: `0.34930995516479013`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing required sections; round2: Missing required sections']`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Maize is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.9669
Season-adjusted confidence: 0.3493 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
maize (raw=0.9669, suit=0.38, adj=0.3493); mothbeans (raw=0.0080, suit=0.38, adj=0.0029); blackgram (raw=0.0023, suit=0.38, adj=0.0008)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## r3_p03_risk_focus

**Prompt**

> Focus on uncertainty and tell me when I should postpone planting.

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `0.07261992389336228`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing raw/adjusted confidence terms; round2: Missing required sections']`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Jute is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.2010
Season-adjusted confidence: 0.0726 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
jute (raw=0.2010, suit=0.38, adj=0.0726); rice (raw=0.0481, suit=0.38, adj=0.0174); mungbean (raw=0.0463, suit=0.38, adj=0.0167)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## r3_p04_location_lucknow

**Prompt**

> Use location enrichment for Lucknow and explain confidence limits.

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `0.19604692073911428`
- Warnings: `['Weather values are estimated from Open-Meteo current conditions.', 'SoilGrids pH unavailable at this point; using fallback pH=6.5.', 'Soil values are estimated from SoilGrids.', 'Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing required sections; round2: Contains internal reasoning leak']`
- Inferred Tools Used: `['geocode_location', 'get_soil_properties', 'get_weather']`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Jute is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.6030
Season-adjusted confidence: 0.1960 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
jute (raw=0.6030, suit=0.46, adj=0.1960); coffee (raw=0.3203, suit=0.46, adj=0.1041); mothbeans (raw=0.0090, suit=0.46, adj=0.0029)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## r3_p05_location_guwahati

**Prompt**

> For Guwahati, give recommendation and a conservative plan if confidence is low.

- Expected HTTP: `200`
- Final Crop: `coffee`
- Confidence: `0.375676417350769`
- Warnings: `['Weather values are estimated from Open-Meteo current conditions.', 'SoilGrids pH unavailable at this point; using fallback pH=6.5.', 'Soil values are estimated from SoilGrids.', 'Localization strength is limited; rerank based on coarse zone match.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Action checklist must contain exactly 3 bullet points; round2: Missing required sections']`
- Inferred Tools Used: `['geocode_location', 'get_soil_properties', 'get_weather']`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Coffee is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.9822
Season-adjusted confidence: 0.3757 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
coffee (raw=0.9822, suit=0.46, adj=0.3757); mothbeans (raw=0.0020, suit=0.46, adj=0.0008); jute (raw=0.0014, suit=0.46, adj=0.0005)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## r3_p06_shap_tradeoff

**Prompt**

> Compare top 3 crops and mention strongest SHAP signal briefly.

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `0.0859405742958188`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing required sections; round2: Missing required sections']`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Jute is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.2379
Season-adjusted confidence: 0.0859 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
jute (raw=0.2379, suit=0.38, adj=0.0859); cotton (raw=0.0683, suit=0.38, adj=0.0247); rice (raw=0.0521, suit=0.38, adj=0.0188)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## r3_p07_no_tools_directive

**Prompt**

> Do not call any external tools. Provide recommendation only from given features.

- Expected HTTP: `200`
- Final Crop: `coffee`
- Confidence: `0.7822356167435647`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'LLM fallback applied: validation_failed: Missing raw/adjusted confidence terms; round2: Missing required sections']`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Coffee is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.8765
Season-adjusted confidence: 0.7822 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
coffee (raw=0.8765, suit=1.00, adj=0.7822); jute (raw=0.1089, suit=1.00, adj=0.0972); rice (raw=0.0012, suit=1.00, adj=0.0011)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
No high-risk warning: adjusted confidence is at or above threshold.
```

## r3_p08_missing_npk_refusal

**Prompt**

> I only know my location and pH. Decide crop for me.

- Expected HTTP: `400`
- Status: `PASSED (expected non-200)`
- HTTP: `400`
- Response: `{'detail': {'message': 'Missing required N/P/K values. Cannot fabricate these features.', 'missing_features': ['N', 'P', 'K'], 'hint': 'Provide soil test values for N, P, K.'}}`
- Quality Score: `100` (required_hits=0, bullets=0, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
N/A (expected non-200 case)
```

## r3_p09_calendar_or_rerank_conflict

**Prompt**

> If reranking changes top crop, explain that conflict clearly.

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `0.17794377330690622`
- Warnings: `['Weather values are estimated from Open-Meteo current conditions.', 'SoilGrids pH unavailable at this point; using fallback pH=6.5.', 'Soil values are estimated from SoilGrids.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Contains internal reasoning leak; round2: Missing required sections']`
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

## r3_p10_research_style

**Prompt**

> Provide a technical explanation with SHAP and LIME for a researcher.

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `0.0777705500461161`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Contains internal reasoning leak; round2: Missing required sections']`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Jute is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.2153
Season-adjusted confidence: 0.0778 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
jute (raw=0.2153, suit=0.38, adj=0.0778); cotton (raw=0.0680, suit=0.38, adj=0.0246); blackgram (raw=0.0675, suit=0.38, adj=0.0244)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## r3_p11_market_note

**Prompt**

> Keep agronomy first but add a brief market-risk note.

- Expected HTTP: `200`
- Final Crop: `jute`
- Confidence: `0.10682069327682257`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Contains internal reasoning leak; round2: Contains internal reasoning leak']`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Jute is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.2957
Season-adjusted confidence: 0.1068 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
jute (raw=0.2957, suit=0.38, adj=0.1068); maize (raw=0.0508, suit=0.38, adj=0.0184); rice (raw=0.0487, suit=0.38, adj=0.0176)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```

## r3_p12_input_quality_advice

**Prompt**

> What additional field measurements should I collect before planting?

- Expected HTTP: `200`
- Final Crop: `maize`
- Confidence: `0.3459504401683807`
- Warnings: `['Localization strength is limited; rerank based on coarse zone match.', 'Model disagreement detected.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing required sections; round2: Missing required sections']`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Maize is selected after ICAR RAG reranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.9576
Season-adjusted confidence: 0.3460 (after ICAR RAG rerank). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
maize (raw=0.9576, suit=0.38, adj=0.3460); mothbeans (raw=0.0164, suit=0.38, adj=0.0059); blackgram (raw=0.0023, suit=0.38, adj=0.0008)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate local weather and irrigation conditions against current season.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan and manual agronomy review.
```
