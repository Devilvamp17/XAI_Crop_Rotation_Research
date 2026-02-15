# Evaluation Report

Output directory: `/home/arnav/coding/research/xai/XAI_Crop_Rotation_Research/evaluation/out/2026-02-15T11-02-36Z`

## 1. Model Performance
- Table: `tables/model_performance.csv`
- Table (markdown): `tables/model_performance.md`
- Confidence distribution: `tables/confidence_distribution.csv`
- Top-k plot: `plots/topk_accuracy_bar.png`
- Confusion matrices: see `plots/confusion_matrix_*.png`

## 2. Calibration
- Table: `tables/calibration_metrics.csv`
- Curves: see `plots/calibration_curve_*.png`

## 3. XAI Quality
- Table: `tables/xai_report.csv`
- Stability overlap curve: `plots/stability_overlap_curve.png`
- Stability rank correlation curve: `plots/stability_rankcorr_curve.png`
- SHAP-LIME overlap: `plots/shap_vs_lime_overlap_bar.png`

## 4. LLM Quality + Reliability
- Table: `tables/llm_quality.csv`
- Plot: `plots/llm_quality_bars.png`

## 5. Component-wise Necessity (Ablation Proxies)
- Table: `tables/ablation_table.csv`
- Plot: `plots/ablation_deltas_bar.png`
- Summary JSON: `summary/ablation_summary.json`

### Key Ablation Rows
- `full` | `mean_final_confidence` | full=0.2977985772853037 | ablated/proxy=0.2977985772853037 | delta=0.0
- `no_calendar` | `mean_final_confidence` | full=0.2977985772853037 | ablated/proxy=0.5519541990466235 | delta=0.2541556217613198
- `no_rag` | `llm_quality_delta` | full=UNAVAILABLE | ablated/proxy=UNAVAILABLE | delta=UNAVAILABLE
- `no_validation` | `invalid_outputs_unblocked_rate` | full=0.0 | ablated/proxy=1.3902439024390243 | delta=1.3902439024390243
- `no_disagreement` | `mean_final_confidence` | full=0.2977985772853037 | ablated/proxy=0.3355638770559213 | delta=0.0377652997706176
- `no_quality_factor` | `mean_final_confidence` | full=0.2977985772853037 | ablated/proxy=0.3234029186205348 | delta=0.025604341335231096

## Availability Notes
- [metrics_xai] shap_importance_bar_<model>.png UNAVAILABLE: global importance arrays not present
- [metrics_llm_quality] Latest suite summary missing; derived LLM quality from run archives.
