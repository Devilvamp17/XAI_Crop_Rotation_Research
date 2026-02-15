from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

import api.main as agent_api
import main as model_api

OUT = Path("artifacts") / "reports" / "health_check.json"


def run_checks() -> dict:
    m = TestClient(model_api.app)
    a = TestClient(agent_api.app)

    checks = {}
    checks["model_health"] = m.get("/health").status_code
    checks["agent_health"] = a.get("/health").status_code
    checks["agent_tools"] = a.get("/tools").status_code
    checks["agent_rag_health"] = a.get("/rag/health").status_code
    checks["agent_metrics_xai"] = a.get("/metrics/xai").status_code
    checks["agent_metrics_xai_curves"] = a.get("/metrics/xai_curves").status_code

    ok = all(v == 200 for v in checks.values())
    out = {"ok": ok, "checks": checks}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    print(json.dumps(run_checks(), indent=2))
