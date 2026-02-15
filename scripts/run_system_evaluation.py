from __future__ import annotations

import json
import subprocess
from pathlib import Path

OUT_DIR = Path("artifacts") / "reports"
OUT_JSON = OUT_DIR / "combined_pipeline_evaluation.json"
OUT_MD = OUT_DIR / "combined_pipeline_evaluation.md"


def run_cmd(cmd: list[str]) -> dict:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "cmd": " ".join(cmd),
        "returncode": p.returncode,
        "stdout": p.stdout[-4000:],
        "stderr": p.stderr[-4000:],
    }


def main() -> None:
    steps = []
    steps.append(run_cmd(["uv", "run", "python", "scripts/validate_icar_dataset.py"]))
    steps.append(run_cmd(["uv", "run", "python", "testing/test_icar_reranker.py"]))
    steps.append(run_cmd(["uv", "run", "python", "testing/test_lime_wrapper_fidelity.py"]))
    steps.append(run_cmd(["uv", "run", "python", "scripts/run_prompt_suites_full.py"]))
    steps.append(run_cmd(["uv", "run", "python", "scripts/audit_rag_artifacts.py"]))
    steps.append(run_cmd(["uv", "run", "python", "xai_eval/evaluate.py"]))
    steps.append(run_cmd(["uv", "run", "python", "scripts/evaluate_rag_pipeline.py"]))
    steps.append(run_cmd(["uv", "run", "python", "scripts/health_check_all.py"]))
    steps.append(run_cmd(["uv", "run", "python", "-m", "evaluation.run_all"]))

    overall_ok = all(s["returncode"] == 0 for s in steps)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({"ok": overall_ok, "steps": steps}, indent=2), encoding="utf-8")

    md = ["# Combined Pipeline Evaluation", "", f"Overall OK: `{overall_ok}`", ""]
    for i, s in enumerate(steps, start=1):
        md += [
            f"## Step {i}",
            f"- Command: `{s['cmd']}`",
            f"- Return code: `{s['returncode']}`",
            "- Stdout:",
            "```text",
            s["stdout"].strip(),
            "```",
        ]
        if s["stderr"].strip():
            md += ["- Stderr:", "```text", s["stderr"].strip(), "```"]
        md += [""]

    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(str(OUT_JSON))
    print(str(OUT_MD))


if __name__ == "__main__":
    main()
