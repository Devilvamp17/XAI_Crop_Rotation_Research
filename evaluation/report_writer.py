from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evaluation.io_utils import safe_load_json, write_text


def _rel(path: Path, run_dir: Path) -> str:
    try:
        return str(path.relative_to(run_dir))
    except Exception:
        return str(path)


def _collect_notes(step_outputs: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    for name, out in step_outputs.items():
        if isinstance(out, dict):
            for n in out.get("notes", []) or []:
                notes.append(f"- [{name}] {n}")
    return notes


def run(run_dir: Path, step_outputs: dict[str, Any]) -> dict[str, Any]:
    summary_dir = run_dir / "summary"
    tables_dir = run_dir / "tables"
    plots_dir = run_dir / "plots"

    ablation_summary = safe_load_json(summary_dir / "ablation_summary.json") or {}

    lines: list[str] = []
    lines.append("# Evaluation Report")
    lines.append("")
    lines.append(f"Output directory: `{run_dir}`")
    lines.append("")

    lines.append("## 1. Model Performance")
    lines.append(f"- Table: `{_rel(tables_dir / 'model_performance.csv', run_dir)}`")
    lines.append(f"- Table (markdown): `{_rel(tables_dir / 'model_performance.md', run_dir)}`")
    lines.append(f"- Confidence distribution: `{_rel(tables_dir / 'confidence_distribution.csv', run_dir)}`")
    lines.append(f"- Top-k plot: `{_rel(plots_dir / 'topk_accuracy_bar.png', run_dir)}`")
    lines.append("- Confusion matrices: see `plots/confusion_matrix_*.png`")
    lines.append("")

    lines.append("## 2. Calibration")
    lines.append(f"- Table: `{_rel(tables_dir / 'calibration_metrics.csv', run_dir)}`")
    lines.append("- Curves: see `plots/calibration_curve_*.png`")
    lines.append("")

    lines.append("## 3. XAI Quality")
    lines.append(f"- Table: `{_rel(tables_dir / 'xai_report.csv', run_dir)}`")
    lines.append(f"- Stability overlap curve: `{_rel(plots_dir / 'stability_overlap_curve.png', run_dir)}`")
    lines.append(f"- Stability rank correlation curve: `{_rel(plots_dir / 'stability_rankcorr_curve.png', run_dir)}`")
    lines.append(f"- SHAP-LIME overlap: `{_rel(plots_dir / 'shap_vs_lime_overlap_bar.png', run_dir)}`")
    lines.append("")

    lines.append("## 4. LLM Quality + Reliability")
    lines.append(f"- Table: `{_rel(tables_dir / 'llm_quality.csv', run_dir)}`")
    lines.append(f"- Plot: `{_rel(plots_dir / 'llm_quality_bars.png', run_dir)}`")
    lines.append("")

    lines.append("## 5. Component-wise Necessity (Ablation Proxies)")
    lines.append(f"- Table: `{_rel(tables_dir / 'ablation_table.csv', run_dir)}`")
    lines.append(f"- Plot: `{_rel(plots_dir / 'ablation_deltas_bar.png', run_dir)}`")
    lines.append(f"- Summary JSON: `{_rel(summary_dir / 'ablation_summary.json', run_dir)}`")

    if ablation_summary.get("rows"):
        lines.append("")
        lines.append("### Key Ablation Rows")
        for row in ablation_summary["rows"][:6]:
            comp = row.get("component_removed", "unknown")
            metric = row.get("metric", "")
            full = row.get("full_value", "UNAVAILABLE")
            abl = row.get("ablated_value_or_proxy", "UNAVAILABLE")
            delta = row.get("delta", "UNAVAILABLE")
            lines.append(f"- `{comp}` | `{metric}` | full={full} | ablated/proxy={abl} | delta={delta}")

    notes = _collect_notes(step_outputs)
    lines.append("")
    lines.append("## Availability Notes")
    if notes:
        lines.extend(notes)
    else:
        lines.append("- None")

    write_text(summary_dir / "report.md", "\n".join(lines) + "\n")
    return {"notes": [], "available": True}
