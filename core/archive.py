from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def new_run_context(endpoint_name: str) -> dict[str, str]:
    request_id = f"req_{secrets.token_hex(4)}"
    timestamp = _timestamp_utc()
    run_dir = Path("artifacts") / "runs" / f"{timestamp}__{request_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return {
        "request_id": request_id,
        "timestamp": timestamp,
        "endpoint_name": endpoint_name,
        "run_dir": str(run_dir),
    }


def write_json(run_dir: str | Path, filename: str, payload: Any) -> Path:
    out = Path(run_dir) / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def write_text(run_dir: str | Path, filename: str, text: str) -> Path:
    out = Path(run_dir) / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return out

