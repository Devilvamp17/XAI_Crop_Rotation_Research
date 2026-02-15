from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.icar_rag_reranker import XAI_FEATURE_BOOST, XAI_FEATURE_BOOST_MAX, rerank_with_icar_rag


def _load_recommendation(run_dir: Path | None) -> dict[str, Any] | None:
    if run_dir:
        p = run_dir / "recommendation.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    runs = Path("artifacts/runs")
    if not runs.exists():
        return None
    all_runs = sorted([x for x in runs.iterdir() if x.is_dir()])
    if not all_runs:
        return None
    p = all_runs[-1] / "recommendation.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _build_demo_payload() -> dict[str, Any]:
    shap_sorted = [
        {"feature": "humidity", "abs_value": 0.18},
        {"feature": "N", "abs_value": 0.12},
        {"feature": "temperature", "abs_value": 0.09},
        {"feature": "K", "abs_value": 0.05},
        {"feature": "P", "abs_value": 0.03},
        {"feature": "ph", "abs_value": 0.02},
    ]
    reranked = rerank_with_icar_rag(
        topk=[
            {"crop": "rice", "confidence": 0.72},
            {"crop": "wheat", "confidence": 0.66},
            {"crop": "maize", "confidence": 0.44},
        ],
        features={"temperature": 29.0, "humidity": 84.0, "ph": 6.8},
        shap_sorted=shap_sorted,
        location=None,
        region="West Bengal",
        month=8,
    )
    adjusted = reranked["adjusted_topk"]
    return {
        "shap": {"sorted_by_abs": shap_sorted},
        "top3": adjusted[:3],
        "rag_rerank": {
            "xai_rag_reasoning": reranked.get("xai_rag_reasoning", {}),
            "zone_resolution": reranked.get("zone_resolution", "unknown"),
        },
        "_source": "demo",
    }


def _extract_curve_inputs(rec: dict[str, Any]) -> tuple[list[str], list[float], dict[str, Any], str]:
    shap_sorted = rec.get("shap", {}).get("sorted_by_abs", [])
    features = [str(x.get("feature", "")) for x in shap_sorted]
    abs_vals = [float(x.get("abs_value", 0.0)) for x in shap_sorted]
    reasoning = rec.get("rag_rerank", {}).get("xai_rag_reasoning") or {}
    top_crop = str((rec.get("top3") or [{}])[0].get("crop", ""))
    return features, abs_vals, reasoning, top_crop


def _plot_shap_cumulative(features: list[str], abs_vals: list[float], out_path: Path) -> None:
    arr = np.array(abs_vals, dtype=float)
    total = float(arr.sum()) if arr.size else 0.0
    if total <= 0:
        cumulative = np.zeros_like(arr)
    else:
        cumulative = np.cumsum(arr) / total
    x = np.arange(1, len(features) + 1)
    plt.figure(figsize=(8, 4.5))
    plt.plot(x, cumulative, marker="o")
    plt.xticks(x, features, rotation=30, ha="right")
    plt.ylim(0, 1.05)
    plt.xlabel("SHAP Feature Rank")
    plt.ylabel("Cumulative |SHAP| Contribution")
    plt.title("Reranker Input SHAP Cumulative Curve")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def _plot_xai_boost_curve(
    features: list[str],
    reasoning: dict[str, Any],
    top_crop: str,
    out_path: Path,
) -> None:
    per_crop = reasoning.get("per_crop", []) if isinstance(reasoning, dict) else []
    entry = next((x for x in per_crop if str(x.get("crop", "")) == top_crop), per_crop[0] if per_crop else {})
    top_feats = [str(x) for x in entry.get("top_shap_features", [])]
    matched = set(str(x) for x in entry.get("matched_features", []))
    ordered = top_feats or features[:3]
    increments = [XAI_FEATURE_BOOST if f in matched else 0.0 for f in ordered]
    if increments:
        capped = []
        run = 0.0
        for inc in increments:
            run = min(run + inc, XAI_FEATURE_BOOST_MAX)
            capped.append(run)
    else:
        capped = []

    x = np.arange(1, len(ordered) + 1)
    plt.figure(figsize=(8, 4.5))
    plt.plot(x, capped, marker="o")
    if len(ordered) > 0:
        plt.xticks(x, ordered, rotation=30, ha="right")
    plt.ylim(0, max(XAI_FEATURE_BOOST_MAX * 1.1, 0.07))
    plt.xlabel("Top SHAP Features Used by Reranker")
    plt.ylabel("Cumulative XAI Boost")
    plt.title(f"Reranker XAI Boost Curve (top crop: {top_crop or 'n/a'})")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot SHAP curves for reranker/XAI integration.")
    parser.add_argument("--run-dir", default="", help="Optional artifacts/runs/<run_dir> path")
    parser.add_argument("--out-dir", default="artifacts/reports")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rec = _load_recommendation(Path(args.run_dir) if args.run_dir else None)
    source = "run"
    if not rec:
        rec = _build_demo_payload()
        source = "demo"

    features, abs_vals, reasoning, top_crop = _extract_curve_inputs(rec)
    if not features:
        rec = _build_demo_payload()
        source = "demo"
        features, abs_vals, reasoning, top_crop = _extract_curve_inputs(rec)

    if not reasoning or not reasoning.get("per_crop"):
        demo = _build_demo_payload()
        if source == "run":
            # Keep run SHAP curve, but use demo for XAI-boost if run has no xai_rag_reasoning yet.
            _, _, reasoning, top_crop = _extract_curve_inputs(demo)
        else:
            features, abs_vals, reasoning, top_crop = _extract_curve_inputs(demo)
            source = "demo"

    shap_curve = out_dir / "reranker_shap_cumulative_curve.png"
    xai_boost_curve = out_dir / "reranker_xai_boost_curve.png"
    summary_json = out_dir / "reranker_shap_curves.json"

    _plot_shap_cumulative(features, abs_vals, shap_curve)
    _plot_xai_boost_curve(features, reasoning, top_crop, xai_boost_curve)

    summary = {
        "source": source,
        "shap_curve": str(shap_curve),
        "xai_boost_curve": str(xai_boost_curve),
        "top_crop": top_crop,
        "features": features,
        "xai_reasoning_present": bool(reasoning and reasoning.get("per_crop")),
    }
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
