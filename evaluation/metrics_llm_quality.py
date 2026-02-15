from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from evaluation.io_utils import (
    list_latest_runs,
    list_latest_suite_dir,
    read_archived_recommendation,
    read_archived_validation,
    write_csv,
    write_md_table,
)


METRIC_KEYS = [
    "success_rate",
    "format_ok_rate",
    "cot_leak_rate",
    "bullets_ok_rate",
    "raw_adjusted_conf_rate",
    "conflict_explained_rate",
    "tool_match_rate",
    "fallback_rate",
]


def _to_rate(v: int, n: int) -> float:
    return float(v / n) if n > 0 else 0.0


def _from_suite(summary: dict[str, Any]) -> dict[str, Any]:
    total = int(summary.get("cases_total", 0))
    passed = int(summary.get("cases_passed_http", 0))
    m = summary.get("metrics", {})
    out = {
        "success_rate": _to_rate(passed, total),
        "format_ok_rate": _to_rate(int(m.get("format_ok", 0)), total),
        "cot_leak_rate": 1.0 - _to_rate(int(m.get("no_cot_leak", 0)), total),
        "bullets_ok_rate": _to_rate(int(m.get("has_3_bullets_only", 0)), total),
        "raw_adjusted_conf_rate": _to_rate(int(m.get("raw_and_adjusted_confidence_present", 0)), total),
        "conflict_explained_rate": _to_rate(int(m.get("calendar_conflict_explained_when_needed", 0)), total),
        "tool_match_rate": _to_rate(int(m.get("tools_used_match_expected", 0)), total),
        "fallback_rate": "UNAVAILABLE",
        "source": "latest_suite",
    }
    return out


def _from_runs() -> dict[str, Any]:
    runs = list_latest_runs(300)
    if not runs:
        return {k: "UNAVAILABLE" for k in [*METRIC_KEYS, "source"]} | {"source": "none"}

    n = len(runs)
    format_ok = 0
    cot_leak = 0
    bullets_ok = 0
    conf_terms_ok = 0
    conflict_ok = 0
    fallback = 0

    for run in runs:
        v = read_archived_validation(run) or {}
        r = read_archived_recommendation(run) or {}
        if v.get("format_ok"):
            format_ok += 1
        if v.get("cot_leak"):
            cot_leak += 1
        if v.get("bullets_ok"):
            bullets_ok += 1
        if v.get("confidence_terms_ok"):
            conf_terms_ok += 1
        if v.get("calendar_conflict_ok", True):
            conflict_ok += 1
        warns = (r.get("warnings") or []) if isinstance(r, dict) else []
        if any("fallback applied" in str(w).lower() for w in warns):
            fallback += 1

    return {
        "success_rate": 1.0,
        "format_ok_rate": _to_rate(format_ok, n),
        "cot_leak_rate": _to_rate(cot_leak, n),
        "bullets_ok_rate": _to_rate(bullets_ok, n),
        "raw_adjusted_conf_rate": _to_rate(conf_terms_ok, n),
        "conflict_explained_rate": _to_rate(conflict_ok, n),
        "tool_match_rate": "UNAVAILABLE",
        "fallback_rate": _to_rate(fallback, n),
        "source": "latest_runs",
    }


def _plot_bars(row: dict[str, Any], out: Path) -> None:
    data = []
    for k in [
        "success_rate",
        "format_ok_rate",
        "cot_leak_rate",
        "bullets_ok_rate",
        "raw_adjusted_conf_rate",
        "conflict_explained_rate",
        "fallback_rate",
    ]:
        v = row.get(k)
        if isinstance(v, (int, float)):
            data.append({"metric": k, "value": float(v)})

    if not data:
        return

    df = pd.DataFrame(data)
    plt.figure(figsize=(9, 4.5))
    sns.barplot(data=df, x="metric", y="value", color="#0891b2")
    plt.xticks(rotation=25, ha="right")
    plt.ylim(0, 1.05)
    plt.title("LLM Quality Metrics")
    plt.tight_layout()
    plt.savefig(out, dpi=200)
    plt.close()


def run(run_dir: Path) -> dict[str, Any]:
    notes: list[str] = []
    tables_dir = run_dir / "tables"
    plots_dir = run_dir / "plots"

    suite_dir = list_latest_suite_dir()
    row: dict[str, Any]
    if suite_dir and (suite_dir / "compliance_summary.json").exists():
        import json

        summary = json.loads((suite_dir / "compliance_summary.json").read_text(encoding="utf-8"))
        row = _from_suite(summary)
    else:
        row = _from_runs()
        notes.append("Latest suite summary missing; derived LLM quality from run archives.")

    df = pd.DataFrame([row])
    write_csv(df, tables_dir / "llm_quality.csv")
    write_md_table(df, tables_dir / "llm_quality.md", "LLM Quality")

    try:
        _plot_bars(row, plots_dir / "llm_quality_bars.png")
    except Exception as exc:
        notes.append(f"Failed plotting llm_quality_bars.png: {exc}")

    return {"notes": notes, "available": True}
