from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.icar_rag_reranker import rerank_with_icar_rag


def test_punjab_rabi_wheat_over_rice() -> None:
    topk = [
        {"crop": "rice", "confidence": 0.80},
        {"crop": "wheat", "confidence": 0.70},
    ]
    features = {"temperature": 14.0, "humidity": 55.0, "ph": 7.2}
    out = rerank_with_icar_rag(topk=topk, features=features, location=None, region="Punjab", month=1)
    assert out["season"] == "rabi"
    assert out["zone_resolution"] in {"state", "district"}
    assert out["adjusted_topk"][0]["crop"] == "wheat"


def test_west_bengal_kharif_rice_over_wheat() -> None:
    topk = [
        {"crop": "wheat", "confidence": 0.80},
        {"crop": "rice", "confidence": 0.72},
    ]
    features = {"temperature": 29.0, "humidity": 88.0, "ph": 6.6}
    out = rerank_with_icar_rag(topk=topk, features=features, location=None, region="West Bengal", month=8)
    assert out["season"] == "kharif"
    assert out["adjusted_topk"][0]["crop"] == "rice"


def test_unknown_location_default_behavior() -> None:
    topk = [
        {"crop": "wheat", "confidence": 0.75},
        {"crop": "rice", "confidence": 0.70},
    ]
    features = {"temperature": 25.0, "humidity": 60.0, "ph": 6.8}
    out = rerank_with_icar_rag(topk=topk, features=features, location=None, region="Atlantis", month=8)
    assert out["zone_resolution"] == "unknown"
    assert len(out["adjusted_topk"]) == 2
    assert all(0.0 <= x["rag_suitability"] <= 1.0 for x in out["adjusted_topk"])


def test_xai_rag_reasoning_is_exposed() -> None:
    topk = [
        {"crop": "rice", "confidence": 0.70},
        {"crop": "maize", "confidence": 0.65},
    ]
    features = {"temperature": 29.0, "humidity": 80.0, "ph": 6.7}
    shap_sorted = [
        {"feature": "humidity", "abs_value": 0.12},
        {"feature": "N", "abs_value": 0.10},
        {"feature": "temperature", "abs_value": 0.08},
    ]
    out = rerank_with_icar_rag(
        topk=topk,
        features=features,
        shap_sorted=shap_sorted,
        location=None,
        region="West Bengal",
        month=8,
    )
    assert "xai_rag_reasoning" in out
    reasoning = out["xai_rag_reasoning"]
    assert reasoning.get("enabled") is True
    assert "humidity" in reasoning.get("top_shap_features", [])
    assert isinstance(reasoning.get("per_crop"), list)
    assert len(reasoning["per_crop"]) == len(topk)
    assert "xai_feature_matches" in out["adjusted_topk"][0]["explanation_tokens"]


if __name__ == "__main__":
    test_punjab_rabi_wheat_over_rice()
    test_west_bengal_kharif_rice_over_wheat()
    test_unknown_location_default_behavior()
    test_xai_rag_reasoning_is_exposed()
    print("ICAR reranker tests passed.")
