from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from evaluation.config import ABLATIONS
from evaluation.io_utils import list_latest_runs, read_archived_recommendation, read_archived_validation, write_csv, write_md_table


def _safe_float(v: Any) -> float | None:
    try:
        return float(v)
    except Exception:
        return None


def _numeric_delta(full_val: Any, abl_val: Any) -> float | str:
    f = _safe_float(full_val)
    a = _safe_float(abl_val)
    if f is None or a is None:
        return "UNAVAILABLE"
    return a - f


def run(run_dir: Path) -> dict[str, Any]:
    notes: list[str] = []
    tables_dir = run_dir / "tables"
    plots_dir = run_dir / "plots"
    summary_dir = run_dir / "summary"

    runs = list_latest_runs(300)
    if not runs:
        notes.append("No archived runs available for ablation proxy analysis.")

    conf_full: list[float] = []
    conf_no_calendar: list[float] = []
    conf_no_quality: list[float] = []
    conf_no_disagreement: list[float] = []
    conflict_count = 0
    disagreement_count = 0

    format_fail_count = 0
    cot_fail_count = 0
    bullets_fail_count = 0

    for rdir in runs:
        rec = read_archived_recommendation(rdir) or {}
        val = read_archived_validation(rdir) or {}

        c = _safe_float(rec.get("confidence"))
        if c is not None:
            conf_full.append(c)

        cc = rec.get("confidence_components", {}) if isinstance(rec, dict) else {}
        raw = _safe_float(cc.get("raw_model_confidence"))
        cal_term = _safe_float(cc.get("calendar_term"))
        dq = _safe_float(cc.get("data_quality_factor"))
        dm = _safe_float(cc.get("disagreement_multiplier"))

        if raw is not None and dq is not None and dm is not None:
            conf_no_calendar.append(raw * dq * dm)
        if raw is not None and cal_term is not None and dm is not None:
            conf_no_quality.append(raw * cal_term * dm)
        if raw is not None and cal_term is not None and dq is not None:
            conf_no_disagreement.append(raw * cal_term * dq)

        if rec.get("calendar_conflict"):
            conflict_count += 1
        if rec.get("agreement_metrics", {}).get("disagreement_detected"):
            disagreement_count += 1

        if not val.get("format_ok", True):
            format_fail_count += 1
        if val.get("cot_leak", False):
            cot_fail_count += 1
        if not val.get("bullets_ok", True):
            bullets_fail_count += 1

    n = max(len(runs), 1)
    full_mean = sum(conf_full) / len(conf_full) if conf_full else "UNAVAILABLE"

    table_rows = [
        {
            "component_removed": "full",
            "metric": "mean_final_confidence",
            "full_value": full_mean,
            "ablated_value_or_proxy": full_mean,
            "delta": 0.0 if isinstance(full_mean, float) else "UNAVAILABLE",
            "notes": "baseline from archived full pipeline",
        },
        {
            "component_removed": "no_calendar",
            "metric": "mean_final_confidence",
            "full_value": full_mean,
            "ablated_value_or_proxy": (sum(conf_no_calendar) / len(conf_no_calendar)) if conf_no_calendar else "UNAVAILABLE",
            "delta": _numeric_delta(full_mean, (sum(conf_no_calendar) / len(conf_no_calendar)) if conf_no_calendar else "UNAVAILABLE"),
            "notes": f"proxy using raw*dq*disagreement; calendar_conflict_rate={conflict_count/n:.4f}",
        },
        {
            "component_removed": "no_rag",
            "metric": "llm_quality_delta",
            "full_value": "UNAVAILABLE",
            "ablated_value_or_proxy": "UNAVAILABLE",
            "delta": "UNAVAILABLE",
            "notes": "no controlled with/without-RAG paired run found",
        },
        {
            "component_removed": "no_validation",
            "metric": "invalid_outputs_unblocked_rate",
            "full_value": 0.0,
            "ablated_value_or_proxy": (format_fail_count + cot_fail_count + bullets_fail_count) / n,
            "delta": (format_fail_count + cot_fail_count + bullets_fail_count) / n,
            "notes": "proxy from archived validation failures prevented by validation layer",
        },
        {
            "component_removed": "no_disagreement",
            "metric": "mean_final_confidence",
            "full_value": full_mean,
            "ablated_value_or_proxy": (sum(conf_no_disagreement) / len(conf_no_disagreement)) if conf_no_disagreement else "UNAVAILABLE",
            "delta": _numeric_delta(full_mean, (sum(conf_no_disagreement) / len(conf_no_disagreement)) if conf_no_disagreement else "UNAVAILABLE"),
            "notes": f"proxy; disagreement_detected_rate={disagreement_count/n:.4f}",
        },
        {
            "component_removed": "no_quality_factor",
            "metric": "mean_final_confidence",
            "full_value": full_mean,
            "ablated_value_or_proxy": (sum(conf_no_quality) / len(conf_no_quality)) if conf_no_quality else "UNAVAILABLE",
            "delta": _numeric_delta(full_mean, (sum(conf_no_quality) / len(conf_no_quality)) if conf_no_quality else "UNAVAILABLE"),
            "notes": "proxy from confidence_components",
        },
    ]

    df = pd.DataFrame(table_rows)
    write_csv(df, tables_dir / "ablation_table.csv")
    write_md_table(df, tables_dir / "ablation_table.md", "Ablation Table")

    # plot numeric deltas only
    plot_df = df.copy()
    plot_df["delta_num"] = pd.to_numeric(plot_df["delta"], errors="coerce")
    plot_df = plot_df.dropna(subset=["delta_num"])
    if not plot_df.empty:
        plt.figure(figsize=(8, 4.5))
        sns.barplot(data=plot_df, x="component_removed", y="delta_num", color="#9333ea")
        plt.title("Ablation Delta (Proxy)")
        plt.xlabel("Component Removed")
        plt.ylabel("Delta")
        plt.xticks(rotation=20, ha="right")
        plt.tight_layout()
        plt.savefig(plots_dir / "ablation_deltas_bar.png", dpi=200)
        plt.close()
    else:
        notes.append("ablation_deltas_bar.png unavailable: no numeric deltas")

    ablation_summary = {
        "ablations": ABLATIONS,
        "rows": table_rows,
        "notes": notes,
    }
    (summary_dir / "ablation_summary.json").write_text(json.dumps(ablation_summary, indent=2), encoding="utf-8")
    return {"notes": notes, "available": True}
