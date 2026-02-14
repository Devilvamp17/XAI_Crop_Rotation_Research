# LLM Prompt Test Outputs

Generated: 2026-02-14T05:27:24.654260Z
Model API: `http://127.0.0.1:8000`
Agent API: `http://127.0.0.1:8100`

## r2_p01_standard

**Prompt**

> Give the recommendation in the strict 5-section format.

- Final Crop: `jute`
- Confidence: `0.09899492263793945`
- Warnings: `['Calendar adjustment changed the top recommendation.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Action checklist must contain exactly 3 bullet points']`
- Inferred Tools Used: `['get_crop_calendar']`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Jute is selected after season-aware re-ranking. Model preferred coffee (raw prob high) but calendar suitability was 0.00, so final is jute.

2) Confidence interpretation
Raw model confidence (from ML): 0.7031
Season-adjusted confidence: 0.0990 (after crop calendar). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
jute (raw=0.2828, suit=0.30, adj=0.0990); coffee (raw=0.7031, suit=0.00, adj=0.0352); blackgram (raw=0.0025, suit=0.00, adj=0.0001)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate recent field weather against model assumptions.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan, prefer in-season options, and do manual agronomy review.
```

## r2_p02_location_india

**Prompt**

> Use location enrichment for Mumbai and explain uncertainty clearly.

- Final Crop: `jute`
- Confidence: `0.165491646528244`
- Warnings: `['Weather values are estimated from Open-Meteo current conditions.', 'SoilGrids pH unavailable at this point; using fallback pH=6.5.', 'Soil values are estimated from SoilGrids.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing required sections']`
- Inferred Tools Used: `['geocode_location', 'get_crop_calendar', 'get_soil_properties', 'get_weather']`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Jute is selected after season-aware re-ranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.4728
Season-adjusted confidence: 0.1655 (after crop calendar). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
jute (raw=0.4728, suit=0.30, adj=0.1655); coffee (raw=0.4246, suit=0.00, adj=0.0212); blackgram (raw=0.0183, suit=0.00, adj=0.0009)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate recent field weather against model assumptions.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan, prefer in-season options, and do manual agronomy review.
```

## r2_p03_calendar_conflict

**Prompt**

> If calendar changes top crop, explain why and suggest fallback.

- Final Crop: `jute`
- Confidence: `0.04320978820323944`
- Warnings: `['Weather values are estimated from Open-Meteo current conditions.', 'SoilGrids pH unavailable at this point; using fallback pH=6.5.', 'Soil values are estimated from SoilGrids.', 'Calendar adjustment changed the top recommendation.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing raw/adjusted confidence terms']`
- Inferred Tools Used: `['geocode_location', 'get_crop_calendar', 'get_soil_properties', 'get_weather']`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Jute is selected after season-aware re-ranking. Model preferred coffee (raw prob high) but calendar suitability was 0.00, so final is jute.

2) Confidence interpretation
Raw model confidence (from ML): 0.6302
Season-adjusted confidence: 0.0432 (after crop calendar). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
jute (raw=0.1235, suit=0.30, adj=0.0432); coffee (raw=0.6302, suit=0.00, adj=0.0315); rice (raw=0.0307, suit=0.40, adj=0.0138)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate recent field weather against model assumptions.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan, prefer in-season options, and do manual agronomy review.
```

## r2_p04_farmer_style

**Prompt**

> Explain for a small farmer with simple language and exactly 3 action bullets.

- Final Crop: `maize`
- Confidence: `0.5784625053405763`
- Warnings: `['Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Missing required sections']`
- Inferred Tools Used: `['get_crop_calendar']`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Maize is selected after season-aware re-ranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.9641
Season-adjusted confidence: 0.5785 (after crop calendar). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
maize (raw=0.9641, suit=0.55, adj=0.5785); mothbeans (raw=0.0093, suit=0.00, adj=0.0005); blackgram (raw=0.0023, suit=0.00, adj=0.0001)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate recent field weather against model assumptions.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan, prefer in-season options, and do manual agronomy review.
```

## r2_p05_no_tools

**Prompt**

> Do not use any external tools. Give concise recommendation.

- Final Crop: `coffee`
- Confidence: `0.9039195746183396`
- Warnings: `['LLM fallback applied: validation_failed: Missing raw/adjusted confidence terms']`
- Inferred Tools Used: `[]`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Coffee is selected after season-aware re-ranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.8609
Season-adjusted confidence: 0.9039 (after crop calendar). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
coffee (raw=0.8609, suit=1.00, adj=0.9039); jute (raw=0.1247, suit=1.00, adj=0.1309); rice (raw=0.0012, suit=1.00, adj=0.0012)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate recent field weather against model assumptions.
- Start with a pilot plot before full-scale planting.

5) Risk warning
No high-risk warning: adjusted confidence is at or above threshold.
```

## r2_p06_missing_npk_fail

**Prompt**

> I only know location, please decide the crop.

- Status: `FAILED`
- HTTP: `400`
- Error: `{'detail': {'message': 'Missing required N/P/K values. Cannot fabricate these features.', 'missing_features': ['N'], 'hint': 'Provide soil test values for N, P, K.'}}`

## r2_p07_technical_xai

**Prompt**

> Give a technical SHAP/LIME-focused summary for an agronomy researcher.

- Final Crop: `jute`
- Confidence: `0.08390088453888893`
- Warnings: `['Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Contains internal reasoning leak']`
- Inferred Tools Used: `['get_crop_calendar']`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Jute is selected after season-aware re-ranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.2397
Season-adjusted confidence: 0.0839 (after crop calendar). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
jute (raw=0.2397, suit=0.30, adj=0.0839); cotton (raw=0.0659, suit=0.35, adj=0.0263); blackgram (raw=0.0654, suit=0.00, adj=0.0033)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate recent field weather against model assumptions.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan, prefer in-season options, and do manual agronomy review.
```

## r2_p08_conservative

**Prompt**

> If confidence is below 0.6, provide a conservative plan with risk warning.

- Final Crop: `maize`
- Confidence: `0.5736905336380006`
- Warnings: `['Weather values are estimated from Open-Meteo current conditions.', 'SoilGrids pH unavailable at this point; using fallback pH=6.5.', 'Soil values are estimated from SoilGrids.', 'Low confidence recommendation (<0.6). Consider manual agronomy review.', 'LLM fallback applied: validation_failed: Contains internal reasoning leak']`
- Inferred Tools Used: `['geocode_location', 'get_crop_calendar', 'get_soil_properties', 'get_weather']`
- Quality Score: `100` (required_hits=5, bullets=3, cot_leaks=[], invalid_tool_mentions=[], no_tools_violation=False, length_ok=True)

**LLM Output**

```text
1) Final recommended crop + short reason
Maize is selected after season-aware re-ranking.

2) Confidence interpretation
Raw model confidence (from ML): 0.9562
Season-adjusted confidence: 0.5737 (after crop calendar). Threshold reference: 0.60

3) Top-3 tradeoff note (if available)
maize (raw=0.9562, suit=0.55, adj=0.5737); mothbeans (raw=0.0168, suit=0.00, adj=0.0008); pigeonpeas (raw=0.0030, suit=0.00, adj=0.0002)

4) Action checklist
- Verify N/P/K with a fresh soil lab test before planting.
- Validate recent field weather against model assumptions.
- Start with a pilot plot before full-scale planting.

5) Risk warning
Low-confidence recommendation. Use conservative plan, prefer in-season options, and do manual agronomy review.
```
