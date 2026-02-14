# Results Evaluation

## Evaluation Scope and Data Availability
This evaluation is based on available repository artifacts and direct re-computation on the provided dataset (`Crop_recommendation.xlsx`, 2200 samples; stratified 80/20 split, test size = 440). Reported quantitative metrics are drawn from:
- model-level re-evaluation on the hold-out split,
- `xai_eval/report.json`,
- `xai_eval/calibration_report.json`,
- `artifacts/llm_prompt_outputs.json` (13 prompt cases; 11 successful, 2 failed).

Where metrics were requested but not present (e.g., insertion faithfulness, explicit what-if curve arrays), they are stated as unavailable.

## 1) Model Performance

### Per-model classification metrics (hold-out split)

| Model | Accuracy | Macro Precision | Macro Recall | Macro F1 | Top-3 Accuracy | ECE |
|---|---:|---:|---:|---:|---:|---:|
| Logistic Regression | 0.9409 | 0.9416 | 0.9409 | 0.9409 | 1.0000 | 0.0174 |
| Random Forest | 0.9682 | 0.9691 | 0.9682 | 0.9678 | 1.0000 | 0.0579 |
| XGBoost | 0.9682 | 0.9685 | 0.9682 | 0.9680 | 0.9977 | 0.0389 |

### Confidence distribution (max-class probability)
- Logistic Regression: mean 0.9351, median 0.9979, P10 0.7347, P90 0.999999
- Random Forest: mean 0.9144, median 0.9800, P10 0.7100, P90 1.0000
- XGBoost: mean 0.9370, median 0.9782, P10 0.8353, P90 0.9823

### Calibration behavior
- Best calibrated by ECE: Logistic Regression (0.0174), then XGBoost (0.0389), then Random Forest (0.0579).
- XGBoost reliability profile (from `xai_eval/calibration_report.json`) is dominated by high-confidence bins (375 samples in 0.9-1.0 bin), where empirical accuracy (0.9973) closely tracks average confidence (0.9719), indicating mild overconfidence but low aggregate miscalibration.

### Model comparison insight
- Random Forest and XGBoost are tied on accuracy; XGBoost offers comparable discriminative quality with better calibration than Random Forest but worse than Logistic Regression.
- Logistic Regression remains competitive and best calibrated despite lower accuracy.

## 2) SHAP Analysis

### Global feature ranking consistency
Mean absolute SHAP rankings (top to lower importance):
- Logistic Regression: `K > P > N > humidity > temperature > ph`
- Random Forest: `humidity > K > P > N > temperature > ph`
- XGBoost: `humidity > P > N > K > temperature > ph`

Interpretation:
- Cross-model consensus is partial: `humidity`, `N`, `P`, `K` dominate across all models, while `ph` is consistently least influential.
- Pairwise SHAP top-3 Jaccard overlap is 0.5 across all model pairs, indicating moderate agreement in salient features.

### Cumulative contribution curve interpretation
From per-instance SHAP (example traces in prompt outputs), the first 2-3 features typically account for the majority of absolute contribution mass. This is consistent with sparse local decision concentration, where a small subset of agronomic variables dominates each recommendation.

### Faithfulness (deletion)
- SHAP deletion AUC: 0.1234 (`xai_eval/report.json`).
- Lower AUC under progressive feature deletion indicates notable probability degradation when top SHAP-ranked features are masked, consistent with faithfulness of feature ranking for decision sensitivity.

### Stability under perturbation
- Top-k overlap: 0.9625
- Rank correlation (Spearman): 0.9790
These values indicate strong explanation stability under small input perturbations.

### Agricultural plausibility
Dominant features (`N`, `P`, `K`, humidity, temperature, pH) are agronomically plausible drivers of crop suitability; the low relative impact of pH in this dataset/modeling context should be interpreted as data- and model-specific rather than universally negligible.

## 3) LIME Analysis

### Local surrogate fidelity
- LIME fidelity R^2: -80.7468
This strongly negative value indicates severe mismatch between local surrogate predictions and black-box probabilities in the current configuration.

### Faithfulness and stability
- LIME deletion AUC: 0.1475
- A dedicated LIME noise-stability curve (e.g., overlap vs perturbation level) is not present in current artifacts; only SHAP stability is explicitly reported.

### Agreement with SHAP
- Explicit per-instance SHAP-LIME top-k overlap summary is not precomputed in artifacts.
- Qualitatively, both methods frequently prioritize nutrient and humidity-related factors, but quantitative agreement metrics should be added to the pipeline for definitive assessment.

### Strengths and weaknesses for tabular agricultural data
- Strength: human-readable rule fragments can support agronomic discussion.
- Weakness: in this setup, poor surrogate fidelity materially limits trustworthiness for quantitative local attribution.

## 4) Multi-Model Agreement

### Prediction agreement
- All-three top-1 agreement rate: 0.9318
- Pairwise top-1 agreement:
  - Logistic vs Random Forest: 0.9455
  - Logistic vs XGBoost: 0.9409
  - Random Forest vs XGBoost: 0.9773

### Probability variance across models
- Mean variance of per-sample max-confidence across models: 0.00363
- Mean standard deviation: 0.0375
This indicates relatively tight confidence dispersion for most samples.

### Trust implications
High agreement and low confidence variance generally support recommendation robustness. However, disagreement cases should be flagged explicitly as higher-uncertainty strata for downstream decision support.

## 5) Constraint and Calendar Impact

From successful prompt-suite runs (n=11):
- Top-1 crop changed after calendar re-ranking in 2/11 cases (18.2%).
- Mean raw top-1 confidence: 0.8367
- Mean adjusted top-1 confidence: 0.3050
- Mean confidence shift (adjusted - raw): -0.5316

Interpretation:
- Calendar constraints materially reduce effective confidence and can alter the final recommendation.
- This confirms non-trivial raw-vs-adjusted conflict behavior, especially when high-probability crops are seasonally unsuitable.
- Interpretability is preserved because the reranking decomposition (raw confidence, suitability, adjusted confidence) is explicit.

## 6) Data Provenance and Uncertainty

- Provenance tagging is explicit (`user`, `weather_api`, `soil_api`, fallback), enabling attribution of uncertainty to data source.
- In prompt-suite records, all successful cases remained below the 0.6 adjusted-confidence threshold (11/11), with the lowest at 0.0427 and highest at 0.5837, indicating conservative post-constraint confidence behavior.
- Estimated weather/soil values are accompanied by warnings; this is appropriate for uncertainty communication.

## 7) Curve Interpretation

### Decision-stages curve
- Intended to represent transition from raw model confidence to calendar-reranked/final adjusted confidence.
- Empirically, stage transition frequently shows substantial downward adjustment when seasonal suitability is modest or zero.

### Top-k confidence curve
- Typically highly peaked: one dominant class probability with sharp drop to ranks 2-3, indicating low ambiguity in raw model space for many instances.

### SHAP cumulative curve
- Rapid early rise implies concentration of attribution mass in first few features; this aligns with sparse local decision mechanisms.

### What-if sensitivity curve
- Not available in current stored artifacts; therefore no quantitative interpretation is reported.

### Stability curve
- Full noise-level curve arrays are not persisted in report; only aggregate stability statistics are available (high overlap/correlation).

### Calibration curve
- High-confidence bins dominate and are mostly well aligned with empirical accuracy; global ECE is low to moderate depending on model.

## 8) LLM Explanation Quality

Based on `artifacts/llm_prompt_outputs.json` (legacy run):
- Completed successfully: 11/13 prompts; failures include one required-input refusal (HTTP 400) and one provider error (HTTP 503 from upstream 402 payment requirement).
- Detected chain-of-thought/self-talk leakage in 3/11 successful outputs.
- Strict 5-section format compliance in only 3/11 successful outputs.
- Explicit raw+adjusted confidence mention in 1/11 outputs.

Interpretation:
- The historical prompt run demonstrates substantial format and faithfulness drift risk.
- The current system architecture includes stricter prompt constraints, output validation, and fallback templating; re-running the suite after these controls is necessary for updated quantitative quality estimates.

## 9) Overall Conclusion

### Strengths
- Strong predictive performance across models (accuracy ~0.94-0.97; near-perfect top-3 accuracy).
- Robust cross-model agreement and low inter-model confidence dispersion.
- Good SHAP stability and explicit confidence decomposition with calendar constraints.
- Clear provenance and uncertainty signaling for enriched inputs.

### Weaknesses
- LIME local fidelity is critically poor in current configuration (negative R^2), limiting interpretability reliability for LIME-derived claims.
- Calendar reranking substantially attenuates confidence, creating frequent low-confidence recommendations that require conservative decision policies.
- Historical LLM output quality showed non-trivial formatting and reasoning-leak violations.

### Novel contributions
- Explicit raw-to-season-adjusted confidence decomposition integrated with recommendation and explanation reporting.
- End-to-end linkage of agronomic constraints, XAI outputs, and LLM advisory with fallback safety.

### Suggested improvements
1. Improve or replace LIME configuration (kernel width, sampling design, or alternative local surrogate methods) and report SHAP-LIME overlap quantitatively.
2. Persist full stability/what-if curve arrays (not only aggregate statistics) for reproducible curve-level analysis.
3. Add insertion-faithfulness metrics and per-model calibration confidence intervals.
4. Re-run the prompt suite under current validation-enabled API and publish updated compliance statistics.
5. Introduce disagreement-aware abstention or review triggers for rare multi-model conflict regions.
