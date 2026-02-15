# Combined Pipeline Evaluation

Overall OK: `True`

## Step 1
- Command: `uv run python scripts/validate_icar_dataset.py`
- Return code: `0`
- Stdout:
```text
[OK] base_rows=108 exploded_rows=19425
```

## Step 2
- Command: `uv run python testing/test_icar_reranker.py`
- Return code: `0`
- Stdout:
```text
ICAR reranker tests passed.
```

## Step 3
- Command: `uv run python testing/test_lime_wrapper_fidelity.py`
- Return code: `0`
- Stdout:
```text
LIME wrapper/fidelity tests passed.
```

## Step 4
- Command: `uv run python scripts/run_prompt_suites_full.py`
- Return code: `0`
- Stdout:
```text
artifacts/reports/prompt_suite_execution_summary.json
artifacts/reports/prompt_suite_execution_summary.md
```

## Step 5
- Command: `uv run python scripts/audit_rag_artifacts.py`
- Return code: `0`
- Stdout:
```text
{
  "summary": {
    "runs_total": 41,
    "runs_with_required_files": 41,
    "zone_resolution_distribution": {
      "unknown": 27,
      "state": 7,
      "district": 7
    },
    "validation_valid_rate": 0.0,
    "fallback_warning_rate": 1.0,
    "geocode_unknown_zone_count": 0,
    "compiled_notes_hit_runs": 0,
    "missing_prompt_output_files": [],
    "suite_dirs_total": 0,
    "suite_dirs_with_compliance_summary": 0
  },
  "issues_count": 1,
  "json": "artifacts/reports/rag_artifact_consistency_audit.json",
  "csv": "artifacts/reports/rag_artifact_consistency_matrix.csv",
  "md": "artifacts/reports/rag_artifact_consistency_audit.md"
}
```

## Step 6
- Command: `uv run python xai_eval/evaluate.py`
- Return code: `0`
- Stdout:
```text
{
  "shap": {
    "deletion_auc": 0.1233927789342124,
    "insertion_auc": 0.6633253107538137
  },
  "lime": {
    "deletion_auc": 0.13723559503113697,
    "insertion_auc": 0.6375603082294886,
    "fidelity_r2": 0.25305185027815585,
    "mean_fidelity_r2": 0.25305185027815585,
    "median_fidelity_r2": 0.2425625371922034,
    "fraction_r2_gt_0": 1.0,
    "status": "reliable"
  },
  "agreement": {
    "shap_lime_topk_jaccard": 0.542,
    "enforce_shap_lime_agreement": true
  },
  "stability": {
    "avg_overlap": 0.98125,
    "avg_rank_corr": 0.9917857142857143
  }
}
```

## Step 7
- Command: `uv run python scripts/evaluate_rag_pipeline.py`
- Return code: `0`
- Stdout:
```text
{
  "total": 3,
  "passed": 3,
  "pass_rate": 1.0,
  "scenarios": [
    {
      "id": "punjab_rabi",
      "expected_top": "wheat",
      "final_top": "wheat",
      "zone_resolution": "state",
      "season": "rabi",
      "passed": true,
      "rerank_conflict": true
    },
    {
      "id": "wb_kharif",
      "expected_top": "rice",
      "final_top": "rice",
      "zone_resolution": "state",
      "season": "kharif",
      "passed": true,
      "rerank_conflict": true
    },
    {
      "id": "unknown_location",
      "expected_top": null,
      "final_top": "rice",
      "zone_resolution": "unknown",
      "season": "kharif",
      "passed": true,
      "rerank_conflict": true
    }
  ]
}
```

## Step 8
- Command: `uv run python scripts/health_check_all.py`
- Return code: `0`
- Stdout:
```text
{
  "ok": true,
  "checks": {
    "model_health": 200,
    "agent_health": 200,
    "agent_tools": 200,
    "agent_rag_health": 200,
    "agent_metrics_xai": 200,
    "agent_metrics_xai_curves": 200
  }
}
```

## Step 9
- Command: `uv run python -m evaluation.run_all`
- Return code: `0`
- Stdout:
```text
/home/arnav/coding/research/xai/XAI_Crop_Rotation_Research/evaluation/out/2026-02-15T11-02-36Z
```
- Stderr:
```text
/home/arnav/coding/research/xai/XAI_Crop_Rotation_Research/.venv/lib/python3.11/site-packages/sklearn/linear_model/_logistic.py:465: ConvergenceWarning: lbfgs failed to converge (status=1):
STOP: TOTAL NO. OF ITERATIONS REACHED LIMIT.

Increase the number of iterations (max_iter) or scale the data as shown in:
    https://scikit-learn.org/stable/modules/preprocessing.html
Please also refer to the documentation for alternative solver options:
    https://scikit-learn.org/stable/modules/linear_model.html#logistic-regression
  n_iter_i = _check_optimize_result(
```
