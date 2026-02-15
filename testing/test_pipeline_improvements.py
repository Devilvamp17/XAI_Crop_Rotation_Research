from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

import api.main as agent_main
from scripts import run_prompt_suite_extensive as suite_ext
from xai_eval.evaluate import run_evaluation


def _predict_disagree(features: dict, models: list[str] | None = None, top_k: int = 3) -> dict:
    return {
        "input": dict(features),
        "models": {
            "xgboost": {
                "model": "xgboost",
                "prediction": {"crop": "rice", "predicted_class": 0, "confidence": 0.90},
                "top3": [
                    {"rank": 1, "crop": "rice", "confidence": 0.90},
                    {"rank": 2, "crop": "maize", "confidence": 0.08},
                    {"rank": 3, "crop": "wheat", "confidence": 0.02},
                ],
                "shap": {"base_value": 0.1, "values": {"N": 0.2}, "sorted_by_abs": [{"feature": "N", "value": 0.2, "abs_value": 0.2}]},
                "lime": {"class_index": 0, "explanations": [{"feature": "N > 80", "weight": 0.2}]},
                "curves": {"topk_confidence": {"x": ["rice", "maize", "wheat"], "y": [0.9, 0.08, 0.02]}},
            },
            "random_forest": {
                "model": "random_forest",
                "prediction": {"crop": "maize", "predicted_class": 1, "confidence": 0.55},
                "top3": [
                    {"rank": 1, "crop": "maize", "confidence": 0.55},
                    {"rank": 2, "crop": "rice", "confidence": 0.30},
                    {"rank": 3, "crop": "wheat", "confidence": 0.15},
                ],
                "shap": {"base_value": 0.1, "values": {"N": 0.2}, "sorted_by_abs": [{"feature": "N", "value": 0.2, "abs_value": 0.2}]},
                "lime": {"class_index": 1, "explanations": [{"feature": "N > 80", "weight": 0.2}]},
                "curves": {"topk_confidence": {"x": ["maize", "rice", "wheat"], "y": [0.55, 0.30, 0.15]}},
            },
            "logistic_regression": {
                "model": "logistic_regression",
                "prediction": {"crop": "rice", "predicted_class": 0, "confidence": 0.51},
                "top3": [
                    {"rank": 1, "crop": "rice", "confidence": 0.51},
                    {"rank": 2, "crop": "maize", "confidence": 0.45},
                    {"rank": 3, "crop": "wheat", "confidence": 0.04},
                ],
                "shap": {"base_value": 0.1, "values": {"N": 0.2}, "sorted_by_abs": [{"feature": "N", "value": 0.2, "abs_value": 0.2}]},
                "lime": {"class_index": 0, "explanations": [{"feature": "N > 80", "weight": 0.2}]},
                "curves": {"topk_confidence": {"x": ["rice", "maize", "wheat"], "y": [0.51, 0.45, 0.04]}},
            },
        },
    }


def test_confidence_decomposition_components_present() -> None:
    client = TestClient(agent_main.app)
    orig_predict = agent_main.model_client.predict
    orig_calendar = agent_main.get_icar_rag_rerank
    try:
        agent_main.model_client.predict = _predict_disagree
        agent_main.get_icar_rag_rerank = lambda region, month: {"rice": 0.1, "maize": 0.9, "wheat": 0.8}
        r = client.post(
            "/recommend",
            json={"N": 90, "P": 42, "K": 43, "temperature": 25.6, "humidity": 71.4, "ph": 6.4},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        cc = body.get("confidence_components", {})
        assert "raw_model_confidence" in cc
        assert "calendar_term" in cc
        assert "data_quality_factor" in cc
        assert "disagreement_multiplier" in cc
        assert "final_confidence" in cc
    finally:
        agent_main.model_client.predict = orig_predict
        agent_main.get_icar_rag_rerank = orig_calendar


def test_rerank_conflict_object_when_rerank_changes_top1() -> None:
    client = TestClient(agent_main.app)
    orig_predict = agent_main.model_client.predict
    orig_calendar = agent_main.get_icar_rag_rerank
    try:
        agent_main.model_client.predict = _predict_disagree
        # maize has much higher suitability than rice to force conflict
        agent_main.get_icar_rag_rerank = lambda region, month: {"rice": 0.0, "maize": 0.95, "wheat": 0.2}
        r = client.post(
            "/recommend",
            json={"N": 90, "P": 42, "K": 43, "temperature": 25.6, "humidity": 71.4, "ph": 6.4},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("rerank_conflict") is not None
        assert body["rerank_conflict"]["previous_top_crop"] == "rice"
    finally:
        agent_main.model_client.predict = orig_predict
        agent_main.get_icar_rag_rerank = orig_calendar


def test_disagreement_warning_when_models_disagree() -> None:
    client = TestClient(agent_main.app)
    orig_predict = agent_main.model_client.predict
    orig_calendar = agent_main.get_icar_rag_rerank
    try:
        agent_main.model_client.predict = _predict_disagree
        agent_main.get_icar_rag_rerank = lambda region, month: {"rice": 0.1, "maize": 0.9, "wheat": 0.8}
        r = client.post(
            "/recommend",
            json={"N": 90, "P": 42, "K": 43, "temperature": 25.6, "humidity": 71.4, "ph": 6.4},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["agreement_metrics"]["disagreement_detected"] is True
        assert any("Model disagreement detected" in w for w in body.get("warnings", []))
    finally:
        agent_main.model_client.predict = orig_predict
        agent_main.get_icar_rag_rerank = orig_calendar


def test_lime_status_unreliable_when_fidelity_low(tmp_path: Path) -> None:
    report = run_evaluation(out_dir=tmp_path)
    lime = report.get("lime", {})
    assert "status" in lime
    if isinstance(lime.get("fidelity_r2"), (int, float)) and lime["fidelity_r2"] < 0.2:
        assert lime["status"] == "unreliable"


def test_xai_eval_outputs_insertion_auc_and_curves_json(tmp_path: Path) -> None:
    run_evaluation(out_dir=tmp_path)
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    curves = json.loads((tmp_path / "curves.json").read_text(encoding="utf-8"))
    assert "insertion_auc" in report.get("shap", {})
    assert "insertion_auc" in report.get("lime", {})
    assert "stability" in curves
    assert "what_if" in curves


def test_prompt_suite_extensive_generates_summary_files(tmp_path: Path) -> None:
    class _Resp:
        def __init__(self, status_code: int, payload: dict[str, Any] | None = None):
            self.status_code = status_code
            self._payload = payload or {}
            self.headers = {"content-type": "application/json"}

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError("http error")

        def json(self) -> dict[str, Any]:
            return self._payload

        @property
        def text(self) -> str:
            return json.dumps(self._payload)

    class _Client:
        def __init__(self, timeout: float = 300.0):
            self.timeout = timeout

        def __enter__(self) -> "_Client":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def get(self, url: str) -> _Resp:
            return _Resp(200, {"status": "ok"})

        def post(self, url: str, json: dict[str, Any]) -> _Resp:
            req = json.get("recommendation_input", {})
            if "N" not in req:
                return _Resp(400, {"detail": {"message": "Missing required N/P/K values."}})
            payload = {
                "recommendation": {
                    "final_crop": "maize",
                    "confidence": 0.5,
                    "tool_calls": ["get_icar_rag_rerank"],
                    "provenance": {"N": {"value": 90, "source": "user"}},
                    "rerank_conflict": None,
                    "shap": {"sorted_by_abs": [{"feature": "N"}]},
                    "rag_rerank": {},
                },
                "llm_response": (
                    "1) Final recommended crop + short reason\n"
                    "Maize with N signal.\n\n"
                    "2) Confidence interpretation\n"
                    "Raw model confidence and adjusted confidence are shown.\n\n"
                    "3) Top-3 tradeoff note (if available)\n"
                    "Tradeoff note.\n\n"
                    "4) Action checklist\n"
                    "- One\n- Two\n- Three\n\n"
                    "5) Risk warning\n"
                    "Low confidence."
                ),
            }
            return _Resp(200, payload)

    orig_client = suite_ext.httpx.Client
    try:
        suite_ext.httpx.Client = _Client
        code = suite_ext.run_suite(agent_api="http://dummy", out_root=tmp_path)
        assert code == 0
        suite_dirs = [p for p in tmp_path.iterdir() if p.is_dir()]
        assert suite_dirs, "suite directory not created"
        suite_dir = suite_dirs[0]
        for fname in ["prompts.json", "results.json", "results.md", "compliance_summary.json"]:
            assert (suite_dir / fname).exists(), f"missing {fname}"
    finally:
        suite_ext.httpx.Client = orig_client


if __name__ == "__main__":
    test_confidence_decomposition_components_present()
    test_rerank_conflict_object_when_rerank_changes_top1()
    test_disagreement_warning_when_models_disagree()
    test_lime_status_unreliable_when_fidelity_low(Path("/tmp/xai_eval_test"))
    test_xai_eval_outputs_insertion_auc_and_curves_json(Path("/tmp/xai_eval_test2"))
    test_prompt_suite_extensive_generates_summary_files(Path("/tmp/suite_test"))
    print("Pipeline improvements tests passed.")
