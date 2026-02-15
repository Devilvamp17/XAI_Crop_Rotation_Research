from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import lime.lime_tabular
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import FEATURE_COLUMNS, load_resources


def _predict_class_probability(model: Any, x_row: pd.DataFrame, class_index: int) -> float:
    proba = model.predict_proba(x_row)[0]
    return float(proba[class_index])


def shap_deletion_auc(
    model: Any,
    x_test: pd.DataFrame,
    shap_explainer: Any,
    baseline: np.ndarray,
    max_samples: int = 50,
) -> float:
    sample_df = x_test.iloc[:max_samples].copy()
    auc_values: list[float] = []

    for _, row in sample_df.iterrows():
        row_df = pd.DataFrame([row.values], columns=x_test.columns)
        pred_class = int(model.predict(row_df)[0])
        class_idx = int(np.where(model.classes_ == pred_class)[0][0])

        shap_vals = shap_explainer.shap_values(row_df)
        if isinstance(shap_vals, list):
            vals = np.abs(np.array(shap_vals[class_idx][0], dtype=float))
        elif isinstance(shap_vals, np.ndarray):
            vals = np.abs(np.array(shap_vals[0, :, class_idx], dtype=float)) if shap_vals.ndim == 3 else np.abs(
                np.array(shap_vals[0], dtype=float)
            )
        else:
            continue

        order = np.argsort(vals)[::-1]
        probs = [_predict_class_probability(model, row_df, class_idx)]

        modified = row.values.astype(float).copy()
        for feat_idx in order:
            modified[feat_idx] = baseline[feat_idx]
            mod_df = pd.DataFrame([modified], columns=x_test.columns)
            probs.append(_predict_class_probability(model, mod_df, class_idx))

        x_axis = np.linspace(0.0, 1.0, len(probs))
        auc = float(np.trapezoid(probs, x_axis))
        auc_values.append(auc)

    return float(np.mean(auc_values)) if auc_values else float("nan")


def lime_fidelity_r2(
    model: Any,
    lime_explainer: lime.lime_tabular.LimeTabularExplainer,
    x_test: pd.DataFrame,
    max_samples: int = 25,
) -> float:
    model_scores: list[float] = []
    lime_scores: list[float] = []
    for _, row in x_test.iloc[:max_samples].iterrows():
        row_array = row.values.astype(float)
        pred_class = int(model.predict(pd.DataFrame([row_array], columns=x_test.columns))[0])
        class_idx = int(np.where(model.classes_ == pred_class)[0][0])

        exp = lime_explainer.explain_instance(
            data_row=row_array,
            predict_fn=lambda arr: model.predict_proba(pd.DataFrame(arr, columns=x_test.columns)),
            num_features=len(x_test.columns),
            num_samples=2000,
            labels=(class_idx,),
        )

        local_pred = exp.local_pred[0] if hasattr(exp, "local_pred") else None
        model_pred = model.predict_proba(pd.DataFrame([row_array], columns=x_test.columns))[0][class_idx]
        if local_pred is not None:
            model_scores.append(float(model_pred))
            lime_scores.append(float(local_pred))

    if len(model_scores) < 2:
        return float("nan")
    return float(r2_score(model_scores, lime_scores))


def lime_deletion_auc(
    model: Any,
    lime_explainer: lime.lime_tabular.LimeTabularExplainer,
    x_test: pd.DataFrame,
    baseline: np.ndarray,
    max_samples: int = 40,
) -> float:
    sample_df = x_test.iloc[:max_samples].copy()
    auc_values: list[float] = []

    for _, row in sample_df.iterrows():
        row_array = row.values.astype(float)
        row_df = pd.DataFrame([row_array], columns=x_test.columns)
        pred_class = int(model.predict(row_df)[0])
        class_idx = int(np.where(model.classes_ == pred_class)[0][0])

        exp = lime_explainer.explain_instance(
            data_row=row_array,
            predict_fn=lambda arr: model.predict_proba(pd.DataFrame(arr, columns=x_test.columns)),
            num_features=len(x_test.columns),
            num_samples=2000,
            labels=(class_idx,),
        )

        fmap = dict(exp.as_map().get(class_idx, []))
        if not fmap:
            continue

        order = sorted(range(len(x_test.columns)), key=lambda i: abs(float(fmap.get(i, 0.0))), reverse=True)
        probs = [_predict_class_probability(model, row_df, class_idx)]

        modified = row_array.copy()
        for feat_idx in order:
            modified[feat_idx] = baseline[feat_idx]
            mod_df = pd.DataFrame([modified], columns=x_test.columns)
            probs.append(_predict_class_probability(model, mod_df, class_idx))

        x_axis = np.linspace(0.0, 1.0, len(probs))
        auc = float(np.trapezoid(probs, x_axis))
        auc_values.append(auc)

    return float(np.mean(auc_values)) if auc_values else float("nan")


def stability_metrics(
    model: Any,
    shap_explainer: Any,
    x_test: pd.DataFrame,
    noise_levels: tuple[float, ...] = (0.01, 0.02, 0.05),
    top_k: int = 3,
    max_samples: int = 40,
) -> dict[str, float]:
    overlaps: list[float] = []
    rank_corrs: list[float] = []

    sample_df = x_test.iloc[:max_samples]

    for _, row in sample_df.iterrows():
        base_df = pd.DataFrame([row.values], columns=x_test.columns)
        pred_class = int(model.predict(base_df)[0])
        class_idx = int(np.where(model.classes_ == pred_class)[0][0])

        base_shap = shap_explainer.shap_values(base_df)
        if isinstance(base_shap, list):
            base_vals = np.array(base_shap[class_idx][0], dtype=float)
        elif isinstance(base_shap, np.ndarray):
            base_vals = np.array(base_shap[0, :, class_idx], dtype=float) if base_shap.ndim == 3 else np.array(
                base_shap[0], dtype=float
            )
        else:
            continue

        base_rank = np.argsort(np.abs(base_vals))[::-1]
        base_topk = set(base_rank[:top_k].tolist())

        for nl in noise_levels:
            noisy = row.values.astype(float).copy()
            noise = np.random.normal(loc=0.0, scale=nl, size=noisy.shape)
            noisy += noise

            noisy_df = pd.DataFrame([noisy], columns=x_test.columns)
            noisy_shap = shap_explainer.shap_values(noisy_df)
            if isinstance(noisy_shap, list):
                noisy_vals = np.array(noisy_shap[class_idx][0], dtype=float)
            elif isinstance(noisy_shap, np.ndarray):
                noisy_vals = np.array(noisy_shap[0, :, class_idx], dtype=float) if noisy_shap.ndim == 3 else np.array(
                    noisy_shap[0], dtype=float
                )
            else:
                continue

            noisy_rank = np.argsort(np.abs(noisy_vals))[::-1]
            noisy_topk = set(noisy_rank[:top_k].tolist())

            inter = len(base_topk.intersection(noisy_topk))
            union = len(base_topk.union(noisy_topk))
            overlap = inter / union if union else 0.0
            overlaps.append(overlap)

            corr, _ = spearmanr(np.abs(base_vals), np.abs(noisy_vals))
            rank_corrs.append(float(corr) if corr is not None and not np.isnan(corr) else 0.0)

    return {
        "avg_overlap": float(np.mean(overlaps)) if overlaps else float("nan"),
        "avg_rank_corr": float(np.mean(rank_corrs)) if rank_corrs else float("nan"),
    }


def calibration_report(model: Any, x_test: pd.DataFrame, y_test: np.ndarray, bins: int = 10) -> dict[str, Any]:
    probs = model.predict_proba(x_test)
    preds = np.argmax(probs, axis=1)
    conf = np.max(probs, axis=1)
    correct = (preds == y_test).astype(float)

    bin_edges = np.linspace(0.0, 1.0, bins + 1)
    avg_confidence: list[float] = []
    accuracy: list[float] = []
    bucket_sizes: list[int] = []

    ece = 0.0
    n = len(conf)

    for i in range(bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        mask = (conf >= lo) & (conf < hi if i < bins - 1 else conf <= hi)
        count = int(np.sum(mask))
        bucket_sizes.append(count)

        if count == 0:
            avg_confidence.append(0.0)
            accuracy.append(0.0)
            continue

        avg_c = float(np.mean(conf[mask]))
        acc = float(np.mean(correct[mask]))
        avg_confidence.append(avg_c)
        accuracy.append(acc)
        ece += abs(acc - avg_c) * (count / n)

    return {
        "bins": [float(x) for x in bin_edges.tolist()],
        "accuracy": accuracy,
        "avg_confidence": avg_confidence,
        "bucket_sizes": bucket_sizes,
        "ece": float(ece),
    }


def run_evaluation(out_dir: Path = Path("xai_eval")) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)

    resources = load_resources()
    model_artifacts = resources["models"]

    data = pd.read_excel(Path("Crop_recommendation.xlsx"))
    x = data[FEATURE_COLUMNS]
    y = resources["label_encoder"].transform(data["label"]) if "label" in data.columns else None
    if y is None:
        raise ValueError("Dataset must contain a 'label' column for evaluation.")

    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42, stratify=y)

    lime_explainer = lime.lime_tabular.LimeTabularExplainer(
        training_data=x_train.values,
        feature_names=FEATURE_COLUMNS,
        class_names=resources["label_encoder"].classes_.tolist(),
        mode="classification",
    )

    baseline = x_train.mean().values

    # Use XGBoost as primary evaluation target for global summary.
    xgb = model_artifacts["xgboost"]["model"]
    xgb_shap = model_artifacts["xgboost"]["shap"]

    result = {
        "shap": {
            "deletion_auc": shap_deletion_auc(xgb, x_test, xgb_shap, baseline),
        },
        "lime": {
            "deletion_auc": lime_deletion_auc(xgb, lime_explainer, x_test, baseline),
            "fidelity_r2": lime_fidelity_r2(xgb, lime_explainer, x_test),
        },
        "stability": stability_metrics(xgb, xgb_shap, x_test),
    }

    calibration = calibration_report(xgb, x_test, y_test)

    (out_dir / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (out_dir / "evaluation_report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (out_dir / "calibration_report.json").write_text(json.dumps(calibration, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    report = run_evaluation()
    print(json.dumps(report, indent=2))
