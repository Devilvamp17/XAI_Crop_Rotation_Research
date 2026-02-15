from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.icar_rag_reranker import rerank_with_icar_rag

OUT_DIR = Path("artifacts") / "reports"
OUT_JSON = OUT_DIR / "rag_rerank_evaluation.json"
OUT_MD = OUT_DIR / "rag_rerank_evaluation.md"


def run_eval() -> dict:
    scenarios = [
        {
            "id": "punjab_rabi",
            "input": {
                "topk": [{"crop": "rice", "confidence": 0.80}, {"crop": "wheat", "confidence": 0.70}],
                "features": {"temperature": 14.0, "humidity": 55.0, "ph": 7.2},
                "location": None,
                "region": "Punjab",
                "month": 1,
            },
            "expected_top": "wheat",
        },
        {
            "id": "wb_kharif",
            "input": {
                "topk": [{"crop": "wheat", "confidence": 0.80}, {"crop": "rice", "confidence": 0.72}],
                "features": {"temperature": 29.0, "humidity": 88.0, "ph": 6.6},
                "location": None,
                "region": "West Bengal",
                "month": 8,
            },
            "expected_top": "rice",
        },
        {
            "id": "unknown_location",
            "input": {
                "topk": [{"crop": "wheat", "confidence": 0.75}, {"crop": "rice", "confidence": 0.70}],
                "features": {"temperature": 25.0, "humidity": 60.0, "ph": 6.8},
                "location": None,
                "region": "Atlantis",
                "month": 8,
            },
            "expected_top": None,
        },
    ]

    rows = []
    pass_count = 0
    for s in scenarios:
        out = rerank_with_icar_rag(**s["input"])
        final_top = out["adjusted_topk"][0]["crop"] if out.get("adjusted_topk") else None
        ok = True if s["expected_top"] is None else (final_top == s["expected_top"])
        pass_count += int(ok)
        rows.append(
            {
                "id": s["id"],
                "expected_top": s["expected_top"],
                "final_top": final_top,
                "zone_resolution": out.get("zone_resolution"),
                "season": out.get("season"),
                "passed": ok,
                "rerank_conflict": bool(out.get("rerank_conflict")),
            }
        )

    summary = {
        "total": len(rows),
        "passed": pass_count,
        "pass_rate": pass_count / len(rows) if rows else 0.0,
        "scenarios": rows,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md = [
        "# RAG Rerank Evaluation",
        "",
        f"Total scenarios: {summary['total']}",
        f"Passed: {summary['passed']}",
        f"Pass rate: {summary['pass_rate']:.2%}",
        "",
    ]
    for r in rows:
        md += [
            f"## {r['id']}",
            f"- Expected top: `{r['expected_top']}`",
            f"- Final top: `{r['final_top']}`",
            f"- Zone resolution: `{r['zone_resolution']}`",
            f"- Season: `{r['season']}`",
            f"- Passed: `{r['passed']}`",
            "",
        ]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run_eval(), indent=2))
