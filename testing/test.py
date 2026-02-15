from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import random
from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient

from main import FEATURE_COLUMNS, app


client = TestClient(app)
EXPECTED_MODELS = ["logistic_regression", "random_forest", "xgboost"]


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _is_sorted_desc(values: list[float]) -> bool:
    return all(values[i] >= values[i + 1] for i in range(len(values) - 1))


def validate_model_block(model_name: str, block: dict[str, Any]) -> None:
    _assert(block["model"] == model_name, f"{model_name}: model name mismatch")

    prediction = block["prediction"]
    _assert(isinstance(prediction["crop"], str) and prediction["crop"], f"{model_name}: invalid crop")
    _assert(isinstance(prediction["predicted_class"], int), f"{model_name}: predicted_class is not int")
    _assert(0.0 <= prediction["confidence"] <= 1.0, f"{model_name}: confidence out of range")

    top3 = block["top3"]
    _assert(len(top3) == 3, f"{model_name}: top3 must have exactly 3 entries")
    confs = [item["confidence"] for item in top3]
    _assert(_is_sorted_desc(confs), f"{model_name}: top3 confidences not sorted descending")
    for idx, item in enumerate(top3, start=1):
        _assert(item["rank"] == idx, f"{model_name}: top3 rank sequence invalid")
        _assert(isinstance(item["crop"], str) and item["crop"], f"{model_name}: top3 crop invalid")
        _assert(0.0 <= item["confidence"] <= 1.0, f"{model_name}: top3 confidence out of range")

    shap_block = block["shap"]
    _assert(isinstance(shap_block["base_value"], float), f"{model_name}: SHAP base_value not float")
    shap_values = shap_block["values"]
    _assert(set(shap_values.keys()) == set(FEATURE_COLUMNS), f"{model_name}: SHAP features mismatch")

    shap_sorted = shap_block["sorted_by_abs"]
    _assert(len(shap_sorted) == len(FEATURE_COLUMNS), f"{model_name}: SHAP sorted length mismatch")
    abs_vals = [float(item["abs_value"]) for item in shap_sorted]
    _assert(_is_sorted_desc(abs_vals), f"{model_name}: SHAP abs values not sorted descending")

    lime_block = block["lime"]
    _assert(isinstance(lime_block["class_index"], int), f"{model_name}: LIME class_index not int")
    exps = lime_block["explanations"]
    _assert(len(exps) > 0, f"{model_name}: LIME explanations empty")
    for item in exps:
        _assert(isinstance(item["feature"], str) and item["feature"], f"{model_name}: LIME feature invalid")
        _assert(isinstance(item["weight"], float), f"{model_name}: LIME weight not float")


def valid_payloads() -> list[dict[str, float]]:
    return [
        {"N": 90, "P": 42, "K": 43, "temperature": 25.6, "humidity": 71.4, "ph": 6.4},
        {"N": 20, "P": 15, "K": 30, "temperature": 18.0, "humidity": 55.0, "ph": 5.6},
        {"N": 120, "P": 60, "K": 80, "temperature": 32.5, "humidity": 88.0, "ph": 7.1},
        {"N": 0, "P": 5, "K": 5, "temperature": 8.0, "humidity": 14.0, "ph": 3.5},
        {"N": 140, "P": 145, "K": 205, "temperature": 44.0, "humidity": 100.0, "ph": 9.9},
    ]


def random_payloads(n: int = 8) -> list[dict[str, float]]:
    rng = random.Random(42)
    out: list[dict[str, float]] = []
    for _ in range(n):
        out.append(
            {
                "N": rng.uniform(0, 140),
                "P": rng.uniform(5, 145),
                "K": rng.uniform(5, 205),
                "temperature": rng.uniform(8.0, 44.0),
                "humidity": rng.uniform(14.0, 100.0),
                "ph": rng.uniform(3.5, 9.9),
            }
        )
    return out


def test_health() -> None:
    r = client.get("/health")
    _assert(r.status_code == 200, f"/health status expected 200, got {r.status_code}")
    body = r.json()
    _assert(body.get("status") == "ok", f"/health body mismatch: {body}")


def test_predict_payload(payload: dict[str, float], label: str) -> None:
    r = client.post("/predict", json=payload)
    _assert(r.status_code == 200, f"{label}: /predict returned {r.status_code} -> {r.text}")
    body = r.json()

    _assert(set(body.keys()) == {"input", "models"}, f"{label}: top-level keys mismatch")
    _assert(set(body["models"].keys()) == set(EXPECTED_MODELS), f"{label}: model keys mismatch")

    for model_name in EXPECTED_MODELS:
        validate_model_block(model_name, body["models"][model_name])


def test_invalid_payloads() -> None:
    missing_field = {"N": 90, "P": 42, "K": 43, "temperature": 25.6, "humidity": 71.4}
    r1 = client.post("/predict", json=missing_field)
    _assert(r1.status_code == 422, f"missing-field payload should fail with 422, got {r1.status_code}")

    wrong_type = {
        "N": "abc",
        "P": 42,
        "K": 43,
        "temperature": 25.6,
        "humidity": 71.4,
        "ph": 6.4,
    }
    r2 = client.post("/predict", json=wrong_type)
    _assert(r2.status_code == 422, f"wrong-type payload should fail with 422, got {r2.status_code}")


def run_all_tests() -> list[CheckResult]:
    checks: list[CheckResult] = []

    def run(name: str, fn) -> None:
        try:
            fn()
            checks.append(CheckResult(name=name, ok=True))
        except Exception as exc:  # noqa: BLE001
            checks.append(CheckResult(name=name, ok=False, detail=str(exc)))

    run("health_endpoint", test_health)
    run("invalid_payloads", test_invalid_payloads)

    for i, payload in enumerate(valid_payloads(), start=1):
        run(f"valid_payload_{i}", lambda p=payload, n=i: test_predict_payload(p, f"valid_payload_{n}"))

    for i, payload in enumerate(random_payloads(), start=1):
        run(f"random_payload_{i}", lambda p=payload, n=i: test_predict_payload(p, f"random_payload_{n}"))

    return checks


def main() -> None:
    checks = run_all_tests()
    failed = [c for c in checks if not c.ok]

    print("=== API TEST SUMMARY ===")
    print(f"Total checks: {len(checks)}")
    print(f"Passed: {len(checks) - len(failed)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("\n=== FAILURES ===")
        for item in failed:
            print(f"- {item.name}: {item.detail}")
        raise SystemExit(1)

    print("\nOK: API is working correctly for all three models.")


if __name__ == "__main__":
    main()
