from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from evaluation.config import ARTIFACTS_DIR


def load_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))


def safe_load_json(path: str | Path) -> dict[str, Any] | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return load_json(p)
    except Exception:
        return None


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    df.to_csv(p, index=False)


def write_md_table(df: pd.DataFrame, path: str | Path, title: str) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    with p.open("w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        if df.empty:
            f.write("No data available.\n")
        else:
            try:
                f.write(df.to_markdown(index=False))
            except Exception:
                # Fallback when optional 'tabulate' dependency is unavailable.
                headers = [str(c) for c in df.columns.tolist()]
                header_line = "| " + " | ".join(headers) + " |\n"
                sep_line = "| " + " | ".join(["---"] * len(headers)) + " |\n"
                f.write(header_line)
                f.write(sep_line)
                for _, row in df.iterrows():
                    vals = [str(row[c]) for c in df.columns]
                    f.write("| " + " | ".join(vals) + " |\n")
            f.write("\n")


def write_text(path: str | Path, text: str) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    p.write_text(text, encoding="utf-8")


def list_latest_suite_dir() -> Path | None:
    suite_root = ARTIFACTS_DIR / "suites"
    if not suite_root.exists():
        return None
    dirs = [p for p in suite_root.iterdir() if p.is_dir()]
    if not dirs:
        return None
    return sorted(dirs, key=lambda x: x.stat().st_mtime, reverse=True)[0]


def list_latest_runs(n: int = 200) -> list[Path]:
    run_root = ARTIFACTS_DIR / "runs"
    if not run_root.exists():
        return []
    dirs = [p for p in run_root.iterdir() if p.is_dir() and "__req_" in p.name]
    dirs = sorted(dirs, key=lambda x: x.stat().st_mtime, reverse=True)
    return dirs[:n]


def _read_run_json(run_dir: Path, filename: str) -> dict[str, Any] | None:
    return safe_load_json(run_dir / filename)


def read_archived_validation(run_dir: Path) -> dict[str, Any] | None:
    return _read_run_json(run_dir, "validation.json")


def read_archived_recommendation(run_dir: Path) -> dict[str, Any] | None:
    return _read_run_json(run_dir, "recommendation.json")


def read_archived_tool_calls(run_dir: Path) -> dict[str, Any] | None:
    value = _read_run_json(run_dir, "tool_calls.json")
    if isinstance(value, list):
        return {"tool_calls": value}
    return value


def read_archived_rag_hits(run_dir: Path) -> dict[str, Any] | None:
    value = _read_run_json(run_dir, "rag_hits.json")
    if isinstance(value, list):
        return {"rag_hits": value}
    return value
