from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from evaluation.config import XAI_EVAL_DIR
from evaluation.io_utils import safe_load_json, write_csv, write_md_table


def _plot_stability_curve(x: list[float], y: list[float], title: str, ylabel: str, out: Path) -> None:
    plt.figure(figsize=(6, 4.5))
    sns.lineplot(x=x, y=y, marker="o")
    plt.xlabel("Noise Level")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out, dpi=200)
    plt.close()


def _plot_bar(labels: list[str], values: list[float], title: str, ylabel: str, out: Path) -> None:
    plt.figure(figsize=(6, 4.5))
    sns.barplot(x=labels, y=values, color="#2563eb")
    plt.title(title)
    plt.ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(out, dpi=200)
    plt.close()


def run(run_dir: Path) -> dict[str, Any]:
    notes: list[str] = []
    tables_dir = run_dir / "tables"
    plots_dir = run_dir / "plots"

    report = safe_load_json(XAI_EVAL_DIR / "report.json") or {}
    curves = safe_load_json(XAI_EVAL_DIR / "curves.json") or {}

    row = {
        "shap_deletion_auc": report.get("shap", {}).get("deletion_auc", "UNAVAILABLE"),
        "shap_insertion_auc": report.get("shap", {}).get("insertion_auc", "UNAVAILABLE"),
        "lime_deletion_auc": report.get("lime", {}).get("deletion_auc", "UNAVAILABLE"),
        "lime_insertion_auc": report.get("lime", {}).get("insertion_auc", "UNAVAILABLE"),
        "lime_fidelity_r2": report.get("lime", {}).get("fidelity_r2", "UNAVAILABLE"),
        "lime_status": report.get("lime", {}).get("status", "UNAVAILABLE"),
        "shap_lime_topk_jaccard": report.get("agreement", {}).get("shap_lime_topk_jaccard", "UNAVAILABLE"),
        "stability_avg_overlap": report.get("stability", {}).get("avg_overlap", "UNAVAILABLE"),
        "stability_avg_rank_corr": report.get("stability", {}).get("avg_rank_corr", "UNAVAILABLE"),
    }
    df = pd.DataFrame([row])
    write_csv(df, tables_dir / "xai_report.csv")
    write_md_table(df, tables_dir / "xai_report.md", "XAI Report")

    stability = curves.get("stability", {})
    nl = stability.get("noise_levels", [])
    ov = stability.get("topk_overlap", [])
    rc = stability.get("rank_corr", [])

    if nl and ov:
        _plot_stability_curve(nl, ov, "Stability Overlap Curve", "Top-k Overlap", plots_dir / "stability_overlap_curve.png")
    else:
        notes.append("stability_overlap_curve.png UNAVAILABLE: missing curves/stability data")

    if nl and rc:
        _plot_stability_curve(nl, rc, "Stability Rank Correlation Curve", "Spearman Rank Corr", plots_dir / "stability_rankcorr_curve.png")
    else:
        notes.append("stability_rankcorr_curve.png UNAVAILABLE: missing curves/stability data")

    lime_samples = curves.get("lime_fidelity_r2_list")
    if isinstance(lime_samples, list) and len(lime_samples) > 0:
        plt.figure(figsize=(6, 4.5))
        sns.histplot(np.array(lime_samples, dtype=float), bins=20, kde=False)
        plt.title("LIME Fidelity Distribution")
        plt.xlabel("R2")
        plt.tight_layout()
        plt.savefig(plots_dir / "lime_fidelity_hist.png", dpi=200)
        plt.close()
    else:
        notes.append("lime_fidelity_hist.png UNAVAILABLE: per-sample LIME fidelity not present")

    if "agreement" in report and isinstance(report["agreement"].get("shap_lime_topk_jaccard"), (int, float)):
        _plot_bar(
            ["SHAP-LIME Overlap"],
            [float(report["agreement"]["shap_lime_topk_jaccard"])],
            "SHAP vs LIME Top-k Overlap",
            "Jaccard",
            plots_dir / "shap_vs_lime_overlap_bar.png",
        )
    else:
        notes.append("shap_vs_lime_overlap_bar.png UNAVAILABLE: overlap metric missing")

    global_importance = curves.get("global_importance", {})
    if isinstance(global_importance, dict) and global_importance:
        for model, imp in global_importance.items():
            labels = list(imp.keys())
            vals = [float(v) for v in imp.values()]
            _plot_bar(labels, vals, f"SHAP Global Importance: {model}", "mean(|SHAP|)", plots_dir / f"shap_importance_bar_{model}.png")
    else:
        notes.append("shap_importance_bar_<model>.png UNAVAILABLE: global importance arrays not present")

    return {"notes": notes, "available": bool(report)}
