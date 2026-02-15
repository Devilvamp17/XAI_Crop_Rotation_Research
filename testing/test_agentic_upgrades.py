from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

import api.main as agent_main


def _fake_predict(features: dict, models: list[str] | None = None, top_k: int = 3) -> dict:
    top = [
        {"rank": 1, "crop": "rice", "confidence": 0.80},
        {"rank": 2, "crop": "maize", "confidence": 0.15},
        {"rank": 3, "crop": "wheat", "confidence": 0.05},
    ][:top_k]
    return {
        "input": features,
        "models": {
            "xgboost": {
                "model": "xgboost",
                "prediction": {"crop": "rice", "predicted_class": 0, "confidence": 0.80},
                "top3": top,
                "shap": {
                    "base_value": 0.1,
                    "values": {"N": 0.2, "P": 0.1, "K": 0.05, "temperature": 0.01, "humidity": 0.03, "ph": -0.02},
                    "sorted_by_abs": [
                        {"feature": "N", "value": 0.2, "abs_value": 0.2},
                        {"feature": "P", "value": 0.1, "abs_value": 0.1},
                    ],
                },
                "lime": {"class_index": 0, "explanations": [{"feature": "N > 80", "weight": 0.2}]},
                "curves": {"topk_confidence": {"x": ["rice", "maize", "wheat"], "y": [0.80, 0.15, 0.05]}},
            }
        },
    }


def _valid_llm_text() -> str:
    return (
        "1) Final recommended crop + short reason\n"
        "Maize after rerank and N is a key driver.\n\n"
        "2) Confidence interpretation\n"
        "Raw model confidence (from ML): 0.8000\n"
        "Season-adjusted confidence: 0.1425 (after ICAR RAG rerank). Threshold reference: 0.60\n\n"
        "3) Top-3 tradeoff note (if available)\n"
        "Model preferred rice but calendar suitability lowered it, so final is maize.\n\n"
        "4) Action checklist\n"
        "- Verify N using a fresh soil test.\n"
        "- Check weather and irrigation plan.\n"
        "- Start with a pilot area.\n\n"
        "5) Risk warning\n"
        "Low-confidence recommendation."
    )


def test_archiving_created_per_request() -> None:
    client = TestClient(agent_main.app)
    original_predict = agent_main.model_client.predict
    original_calendar = agent_main.get_icar_rag_rerank
    original_chat = agent_main.llm_client.chat
    original_rag = agent_main.rag_search
    try:
        agent_main.model_client.predict = _fake_predict
        agent_main.get_icar_rag_rerank = lambda region, month: {"rice": 0.1, "maize": 0.9, "wheat": 0.8}
        agent_main.llm_client.chat = lambda system_prompt, user_prompt: _valid_llm_text()
        agent_main.rag_search = lambda query, k=5: [
            {"id": "chunk_001", "title": "maize", "text": "maize guidance", "source": "rag_corpus/maize_facts.md"}
        ]

        r = client.post(
            "/recommend_with_llm",
            json={
                "query": "Give recommendation",
                "recommendation_input": {"N": 90, "P": 42, "K": 43, "temperature": 25.6, "humidity": 71.4, "ph": 6.4},
            },
        )
        assert r.status_code == 200, r.text
        run_dir = Path(r.json()["archive_run_dir"])
        assert run_dir.exists()
        for name in [
            "request.json",
            "tool_calls.json",
            "rag_hits.json",
            "recommendation.json",
            "llm_rounds.json",
            "llm_response.txt",
            "validation.json",
        ]:
            assert (run_dir / name).exists(), f"missing archived file: {name}"
    finally:
        agent_main.model_client.predict = original_predict
        agent_main.get_icar_rag_rerank = original_calendar
        agent_main.llm_client.chat = original_chat
        agent_main.rag_search = original_rag


def test_rag_search_returns_chunks() -> None:
    hits = agent_main.rag_search("jute crop humidity", k=3)
    assert len(hits) > 0
    assert all("id" in h and "title" in h and "text" in h and "source" in h for h in hits)


def test_llm_round2_only_on_failure() -> None:
    client = TestClient(agent_main.app)
    original_predict = agent_main.model_client.predict
    original_calendar = agent_main.get_icar_rag_rerank
    original_chat = agent_main.llm_client.chat
    original_rag = agent_main.rag_search
    calls = {"n": 0}
    try:
        agent_main.model_client.predict = _fake_predict
        agent_main.get_icar_rag_rerank = lambda region, month: {"rice": 0.1, "maize": 0.9, "wheat": 0.8}
        agent_main.rag_search = lambda query, k=5: []

        def chat_spy(system_prompt: str, user_prompt: str) -> str:
            calls["n"] += 1
            if calls["n"] == 1:
                return "bad output"
            return _valid_llm_text()

        agent_main.llm_client.chat = chat_spy
        r = client.post(
            "/recommend_with_llm",
            json={
                "query": "Give recommendation",
                "recommendation_input": {"N": 90, "P": 42, "K": 43, "temperature": 25.6, "humidity": 71.4, "ph": 6.4},
            },
        )
        assert r.status_code == 200, r.text
        assert calls["n"] == 2, "round2 should run only after round1 failure"
        assert "round2 refinement applied" in " ".join(r.json()["recommendation"]["warnings"]).lower()
    finally:
        agent_main.model_client.predict = original_predict
        agent_main.get_icar_rag_rerank = original_calendar
        agent_main.llm_client.chat = original_chat
        agent_main.rag_search = original_rag


def test_faithfulness_checks_trigger() -> None:
    client = TestClient(agent_main.app)
    original_predict = agent_main.model_client.predict
    original_calendar = agent_main.get_icar_rag_rerank
    original_chat = agent_main.llm_client.chat
    original_rag = agent_main.rag_search
    calls = {"n": 0}
    try:
        agent_main.model_client.predict = _fake_predict
        agent_main.get_icar_rag_rerank = lambda region, month: {"rice": 0.1, "maize": 0.9, "wheat": 0.8}
        agent_main.rag_search = lambda query, k=5: []

        def chat_spy(system_prompt: str, user_prompt: str) -> str:
            calls["n"] += 1
            # Missing SHAP feature mention ("N"), should fail faithfulness check.
            if calls["n"] == 1:
                return (
                    "1) Final recommended crop + short reason\n"
                    "Maize after rerank.\n\n"
                    "2) Confidence interpretation\n"
                    "Raw model confidence (from ML): 0.8\n"
                    "Season-adjusted confidence: 0.14\n\n"
                    "3) Top-3 tradeoff note (if available)\n"
                    "Model preferred rice but calendar suitability lowered it, so final is maize.\n\n"
                    "4) Action checklist\n"
                    "- check soil\n"
                    "- check weather\n"
                    "- pilot test\n\n"
                    "5) Risk warning\n"
                    "Low confidence."
                )
            return _valid_llm_text()

        agent_main.llm_client.chat = chat_spy
        r = client.post(
            "/recommend_with_llm",
            json={
                "query": "Give recommendation",
                "recommendation_input": {"N": 90, "P": 42, "K": 43, "temperature": 25.6, "humidity": 71.4, "ph": 6.4},
            },
        )
        assert r.status_code == 200, r.text
        assert calls["n"] == 2, "faithfulness failure should trigger round2"
        assert r.json()["validation"]["valid"] is True
    finally:
        agent_main.model_client.predict = original_predict
        agent_main.get_icar_rag_rerank = original_calendar
        agent_main.llm_client.chat = original_chat
        agent_main.rag_search = original_rag


if __name__ == "__main__":
    test_archiving_created_per_request()
    test_rag_search_returns_chunks()
    test_llm_round2_only_on_failure()
    test_faithfulness_checks_trigger()
    print("Agentic upgrade tests passed.")

