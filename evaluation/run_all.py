from __future__ import annotations

from pathlib import Path

from evaluation import ablation, metrics_calibration, metrics_llm_quality, metrics_model, metrics_xai, report_writer
from evaluation.config import RUN_ID, make_run_dir


def run_all(run_id: str | None = None) -> Path:
    run_dir = make_run_dir(run_id or RUN_ID)

    outputs = {}
    outputs["metrics_model"] = metrics_model.run(run_dir)
    outputs["metrics_calibration"] = metrics_calibration.run(run_dir)
    outputs["metrics_xai"] = metrics_xai.run(run_dir)
    outputs["metrics_llm_quality"] = metrics_llm_quality.run(run_dir)
    outputs["ablation"] = ablation.run(run_dir)
    outputs["report_writer"] = report_writer.run(run_dir, outputs)

    print(str(run_dir))
    return run_dir


if __name__ == "__main__":
    run_all()
