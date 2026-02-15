from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import lime.lime_tabular
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import (
    FEATURE_COLUMNS,
    LIME_DISCRETIZE_CONTINUOUS,
    LIME_KERNEL_WIDTH,
    LIME_NUM_SAMPLES,
    build_lime_predict_fn,
    load_resources,
)


def _predict_class_probability(model: Any, x_row: pd.DataFrame, class_index: int) -> float:
    proba = model.predict_proba(x_row)[0]
    return float(proba[class_index])


def _shap_importance_for_row(model: Any, shap_explainer: Any, row_df: pd.DataFrame) -> tuple[np.ndarray, int]:
    pred_class = int(model.predict(row_df)[0])
    class_idx = int(np.where(model.classes_ == pred_class)[0][0])
    shap_vals = shap_explainer.shap_values(row_df)
    if isinstance(shap_vals, list):
        vals = np.array(shap_vals[class_idx][0], dtype=float)
    elif isinstance(shap_vals, np.ndarray):
        vals = np.array(shap_vals[0, :, class_idx], dtype=float) if shap_vals.ndim == 3 else np.array(shap_vals[0], dtype=float)
    else:
        raise ValueError("Unsupported SHAP value type")
    return vals, class_idx


def _lime_importance_for_row(
    model: Any,
    lime_explainer: lime.lime_tabular.LimeTabularExplainer,
    row_array: np.ndarray,
    columns: list[str],
    num_samples: int = 5000,
) -> tuple[np.ndarray, int]:
    row_df = pd.DataFrame([row_array], columns=columns)
    pred_class = int(model.predict(row_df)[0])
    class_idx = int(np.where(model.classes_ == pred_class)[0][0])

    exp = lime_explainer.explain_instance(
        data_row=row_array,
        predict_fn=build_lime_predict_fn(model),
        num_features=len(columns),
        num_samples=num_samples,
        labels=(class_idx,),
    )

    fmap = dict(exp.as_map().get(class_idx, []))
    vals = np.array([float(fmap.get(i, 0.0)) for i in range(len(columns))], dtype=float)
    return vals, class_idx


def _deletion_auc(model: Any, x_test: pd.DataFrame, baseline: np.ndarray, importance_fn: Any, max_samples: int = 50) -> float:
    auc_values: list[float] = []
    for _, row in x_test.iloc[:max_samples].iterrows():
        row_array = row.values.astype(float)
        row_df = pd.DataFrame([row_array], columns=x_test.columns)
        vals, class_idx = importance_fn(row_df, row_array)
        order = np.argsort(np.abs(vals))[::-1]
        probs = [_predict_class_probability(model, row_df, class_idx)]
        modified = row_array.copy()
        for feat_idx in order:
            modified[feat_idx] = baseline[feat_idx]
            probs.append(_predict_class_probability(model, pd.DataFrame([modified], columns=x_test.columns), class_idx))
        auc_values.append(float(np.trapezoid(probs, np.linspace(0.0, 1.0, len(probs)))))
    return float(np.mean(auc_values)) if auc_values else float("nan")


def _insertion_auc(model: Any, x_test: pd.DataFrame, baseline: np.ndarray, importance_fn: Any, max_samples: int = 50) -> float:
    auc_values: list[float] = []
    for _, row in x_test.iloc[:max_samples].iterrows():
        row_array = row.values.astype(float)
        row_df = pd.DataFrame([row_array], columns=x_test.columns)
        vals, class_idx = importance_fn(row_df, row_array)
        order = np.argsort(np.abs(vals))[::-1]
        modified = baseline.astype(float).copy()
        probs = []
        for feat_idx in [-1, *order.tolist()]:
            if feat_idx >= 0:
                modified[feat_idx] = row_array[feat_idx]
            probs.append(_predict_class_probability(model, pd.DataFrame([modified], columns=x_test.columns), class_idx))
        auc_values.append(float(np.trapezoid(probs, np.linspace(0.0, 1.0, len(probs)))))
    return float(np.mean(auc_values)) if auc_values else float("nan")


def _lime_kernel_weights(neighborhood: np.ndarray, center: np.ndarray, feature_std: np.ndarray) -> np.ndarray:
    safe_std = np.where(feature_std <= 1e-8, 1.0, feature_std)
    z = (neighborhood - center.reshape(1, -1)) / safe_std.reshape(1, -1)
    distances = np.linalg.norm(z, axis=1)
    return np.sqrt(np.exp(-(distances**2) / max(LIME_KERNEL_WIDTH**2, 1e-8)))


def _lime_fidelity_metrics(model: Any, x_test: pd.DataFrame, feature_std: np.ndarray, max_samples: int = 30) -> dict[str, Any]:
    scores: list[float] = []
    predict_fn = build_lime_predict_fn(model)

    for _, row in x_test.iloc[:max_samples].iterrows():
        row_array = row.values.astype(float)
        row_df = pd.DataFrame([row_array], columns=x_test.columns)
        pred_class = int(model.predict(row_df)[0])
        class_idx = int(np.where(model.classes_ == pred_class)[0][0])

        safe_std = np.where(feature_std <= 1e-8, 1.0, feature_std)
        noise = np.random.normal(loc=0.0, scale=safe_std.reshape(1, -1), size=(max(LIME_NUM_SAMPLES, 5000), row_array.shape[0]))
        neighborhood = row_array.reshape(1, -1) + noise

        y_black_box = predict_fn(neighborhood)[:, class_idx]
        weights = _lime_kernel_weights(neighborhood, row_array, feature_std)

        surrogate = Ridge(alpha=1.0, fit_intercept=True)
        surrogate.fit(neighborhood, y_black_box, sample_weight=weights)
        y_sur = surrogate.predict(neighborhood)
        r2 = float(r2_score(y_black_box, y_sur))
        if np.isfinite(r2):
            scores.append(r2)

    if not scores:
        return {
            "mean_fidelity_r2": float("nan"),
            "median_fidelity_r2": float("nan"),
            "fraction_r2_gt_0": float("nan"),
            "per_sample_r2": [],
        }

    arr = np.asarray(scores, dtype=float)
    return {
        "mean_fidelity_r2": float(np.mean(arr)),
        "median_fidelity_r2": float(np.median(arr)),
        "fraction_r2_gt_0": float(np.mean(arr > 0.0)),
        "per_sample_r2": [float(v) for v in arr.tolist()],
    }


def _stability_curves(model: Any, shap_explainer: Any, x_test: pd.DataFrame, noise_levels: tuple[float, ...] = (0.0, 0.01, 0.02, 0.05), top_k: int = 3, max_samples: int = 40) -> dict[str, Any]:
    overlap_by_level: list[float] = []
    rank_corr_by_level: list[float] = []
    sample_df = x_test.iloc[:max_samples]

    for nl in noise_levels:
        overlaps: list[float] = []
        rank_corrs: list[float] = []
        for _, row in sample_df.iterrows():
            base_df = pd.DataFrame([row.values], columns=x_test.columns)
            base_vals, _ = _shap_importance_for_row(model, shap_explainer, base_df)
            base_topk = set(np.argsort(np.abs(base_vals))[::-1][:top_k].tolist())

            noisy = row.values.astype(float).copy()
            if nl > 0:
                noisy += np.random.normal(loc=0.0, scale=nl, size=noisy.shape)
            noisy_df = pd.DataFrame([noisy], columns=x_test.columns)
            noisy_vals, _ = _shap_importance_for_row(model, shap_explainer, noisy_df)
            noisy_topk = set(np.argsort(np.abs(noisy_vals))[::-1][:top_k].tolist())

            inter = len(base_topk.intersection(noisy_topk))
            union = len(base_topk.union(noisy_topk))
            overlaps.append(inter / union if union else 0.0)

            corr, _ = spearmanr(np.abs(base_vals), np.abs(noisy_vals))
            rank_corrs.append(float(corr) if corr is not None and not np.isnan(corr) else 0.0)

        overlap_by_level.append(float(np.mean(overlaps)) if overlaps else float("nan"))
        rank_corr_by_level.append(float(np.mean(rank_corrs)) if rank_corrs else float("nan"))

    return {
        "noise_levels": [float(x) for x in noise_levels],
        "topk_overlap": overlap_by_level,
        "rank_corr": rank_corr_by_level,
        "avg_overlap": float(np.mean(overlap_by_level)) if overlap_by_level else float("nan"),
        "avg_rank_corr": float(np.mean(rank_corr_by_level)) if rank_corr_by_level else float("nan"),
    }


def _calibration_report(model: Any, x_test: pd.DataFrame, y_test: np.ndarray, bins: int = 10) -> dict[str, Any]:
    probs = model.predict_proba(x_test)
    preds = np.argmax(probs, axis=1)
    conf = np.max(probs, axis=1)
    correct = (preds == y_test).astype(float)
    edges = np.linspace(0.0, 1.0, bins + 1)

    acc: list[float] = []
    avg: list[float] = []
    bucket_sizes: list[int] = []
    ece = 0.0
    for i in range(bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (conf >= lo) & (conf < hi if i < bins - 1 else conf <= hi)
        n = int(np.sum(mask))
        bucket_sizes.append(n)
        if n == 0:
            acc.append(0.0)
            avg.append(0.0)
            continue
        a = float(np.mean(correct[mask]))
        c = float(np.mean(conf[mask]))
        acc.append(a)
        avg.append(c)
        ece += abs(a - c) * (n / len(conf))

    return {
        "bins": edges.tolist(),
        "accuracy": acc,
        "avg_confidence": avg,
        "bucket_sizes": bucket_sizes,
        "ece": float(ece),
    }


def run_evaluation(out_dir: Path = Path("xai_eval")) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)

    resources = load_resources()
    data = pd.read_excel(Path("Crop_recommendation.xlsx"))
    x = data[FEATURE_COLUMNS]
    y = resources["label_encoder"].transform(data["label"]) if "label" in data.columns else None
    if y is None:
        raise ValueError("Dataset must contain label column")

    x_train, x_test, _, y_test = train_test_split(x, y, test_size=0.2, random_state=42, stratify=y)

    xgb = resources["models"]["xgboost"]["model"]
    xgb_shap = resources["models"]["xgboost"]["shap"]

    lime_explainer = lime.lime_tabular.LimeTabularExplainer(
        training_data=x_train.values,
        feature_names=FEATURE_COLUMNS,
        class_names=resources["label_encoder"].inverse_transform(np.asarray(xgb.classes_, dtype=int)).tolist(),
        mode="classification",
        discretize_continuous=LIME_DISCRETIZE_CONTINUOUS,
        kernel_width=LIME_KERNEL_WIDTH,
    )

    baseline = x_train.mean().values
    shap_imp = lambda row_df, row_array: _shap_importance_for_row(xgb, xgb_shap, row_df)
    lime_imp = lambda row_df, row_array: _lime_importance_for_row(xgb, lime_explainer, row_array, row_df.columns.tolist(), LIME_NUM_SAMPLES)

    shap_del = _deletion_auc(xgb, x_test, baseline, shap_imp)
    shap_ins = _insertion_auc(xgb, x_test, baseline, shap_imp)
    lime_del = _deletion_auc(xgb, x_test, baseline, lambda d, a: lime_imp(d, a)[:2])
    lime_ins = _insertion_auc(xgb, x_test, baseline, lambda d, a: lime_imp(d, a)[:2])

    lime_fid = _lime_fidelity_metrics(xgb, x_test, x_train.std().values.astype(float))
    lime_r2 = float(lime_fid.get("mean_fidelity_r2", float("nan")))
    lime_status = "reliable" if lime_r2 >= 0.2 else "unreliable"

    stability = _stability_curves(xgb, xgb_shap, x_test)

    overlap_vals = []
    for _, row in x_test.iloc[:50].iterrows():
        row_array = row.values.astype(float)
        row_df = pd.DataFrame([row_array], columns=x_test.columns)
        svals, _ = _shap_importance_for_row(xgb, xgb_shap, row_df)
        lvals, _ = _lime_importance_for_row(xgb, lime_explainer, row_array, x_test.columns.tolist(), LIME_NUM_SAMPLES)
        sset = set(np.argsort(np.abs(svals))[::-1][:3].tolist())
        lset = set(np.argsort(np.abs(lvals))[::-1][:3].tolist())
        union = len(sset.union(lset))
        overlap_vals.append((len(sset.intersection(lset)) / union) if union else 0.0)

    per_model_calib = {name: _calibration_report(artifact["model"], x_test, y_test) for name, artifact in resources["models"].items()}

    report = {
        "shap": {"deletion_auc": shap_del, "insertion_auc": shap_ins},
        "lime": {
            "deletion_auc": lime_del,
            "insertion_auc": lime_ins,
            "fidelity_r2": lime_r2,
            "mean_fidelity_r2": lime_fid.get("mean_fidelity_r2"),
            "median_fidelity_r2": lime_fid.get("median_fidelity_r2"),
            "fraction_r2_gt_0": lime_fid.get("fraction_r2_gt_0"),
            "status": lime_status,
        },
        "agreement": {
            "shap_lime_topk_jaccard": float(np.mean(overlap_vals)) if overlap_vals else float("nan"),
            "enforce_shap_lime_agreement": lime_status != "unreliable",
        },
        "stability": {"avg_overlap": stability.get("avg_overlap"), "avg_rank_corr": stability.get("avg_rank_corr")},
    }

    curves = {
        "stability": stability,
        "calibration": per_model_calib,
        "lime_fidelity_r2_list": lime_fid.get("per_sample_r2", []),
    }

    calibration = dict(per_model_calib.get("xgboost", {}))
    calibration["per_model"] = per_model_calib

    (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out_dir / "curves.json").write_text(json.dumps(curves, indent=2), encoding="utf-8")
    (out_dir / "calibration_report.json").write_text(json.dumps(calibration, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run_evaluation(), indent=2))
