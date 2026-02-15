from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
XAI_EVAL_DIR = REPO_ROOT / "xai_eval"
DEFAULT_TEST_SPLIT = 0.2
DATASET_PATH = REPO_ROOT / "Crop_recommendation.xlsx"
OUTPUT_ROOT = REPO_ROOT / "evaluation" / "out"
RUN_ID = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
ABLATIONS = ["full", "no_calendar", "no_rag", "no_validation", "no_disagreement", "no_quality_factor"]


def make_run_dir(run_id: str | None = None) -> Path:
    rid = run_id or RUN_ID
    run_dir = OUTPUT_ROOT / rid
    (run_dir / "tables").mkdir(parents=True, exist_ok=True)
    (run_dir / "plots").mkdir(parents=True, exist_ok=True)
    (run_dir / "summary").mkdir(parents=True, exist_ok=True)
    return run_dir
