from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

VALID_PAYLOAD = {
    "N": 90,
    "P": 42,
    "K": 43,
    "temperature": 25.6,
    "humidity": 71.4,
    "ph": 6.4,
}
EXPECTED_MODELS = ["logistic_regression", "random_forest", "xgboost"]
EXPECTED_FEATURES = ["N", "P", "K", "temperature", "humidity", "ph"]


def assert_top3(top3: list[dict]) -> None:
    assert len(top3) == 3, f"top3 length expected 3, got {len(top3)}"
    for item in top3:
        assert "crop" in item
        assert "confidence" in item
        assert 0.0 <= item["confidence"] <= 1.0


def assert_model_payload(model_name: str, payload: dict) -> None:
    assert payload["model"] == model_name
    pred = payload["prediction"]
    assert isinstance(pred["crop"], str)
    assert 0.0 <= pred["confidence"] <= 1.0

    assert_top3(payload["top3"])

    shap_data = payload["shap"]
    assert isinstance(shap_data["base_value"], float)
    assert set(shap_data["values"].keys()) == set(EXPECTED_FEATURES)
    assert len(shap_data["sorted_by_abs"]) == len(EXPECTED_FEATURES)

    lime_data = payload["lime"]
    assert isinstance(lime_data["class_index"], int)
    assert len(lime_data["explanations"]) > 0


def run_tests() -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json().get("status") == "ok"

    response = client.post("/predict", json=VALID_PAYLOAD)
    assert response.status_code == 200, response.text
    body = response.json()

    assert set(body.keys()) == {"input", "models"}
    assert set(body["models"].keys()) == set(EXPECTED_MODELS)

    for model_name in EXPECTED_MODELS:
        assert_model_payload(model_name, body["models"][model_name])

    missing_field = client.post(
        "/predict",
        json={
            "N": 90,
            "P": 42,
            "K": 43,
            "temperature": 25.6,
            "humidity": 71.4,
        },
    )
    assert missing_field.status_code == 422

    print("All API tests passed for all three models.")


if __name__ == "__main__":
    run_tests()
