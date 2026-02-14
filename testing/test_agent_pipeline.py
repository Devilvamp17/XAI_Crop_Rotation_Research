from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from copy import deepcopy

from fastapi.testclient import TestClient

import api.main as agent_main


client = TestClient(agent_main.app)


def _dummy_model_response(features: dict, models: list[str], top_k: int) -> dict:
    return {
        "input": deepcopy(features),
        "models": {
            "xgboost": {
                "model": "xgboost",
                "prediction": {"crop": "rice", "predicted_class": 0, "confidence": 0.91},
                "top3": [
                    {"rank": 1, "crop": "rice", "confidence": 0.91},
                    {"rank": 2, "crop": "maize", "confidence": 0.06},
                    {"rank": 3, "crop": "wheat", "confidence": 0.03},
                ],
                "shap": {"base_value": 0.0, "values": {"N": 0.1, "P": 0.1, "K": 0.1, "temperature": 0.1, "humidity": 0.1, "ph": 0.1}, "sorted_by_abs": []},
                "lime": {"class_index": 0, "explanations": [{"feature": "N > 80", "weight": 0.12}]},
                "curves": {"topk_confidence": {"x": ["rice", "maize", "wheat"], "y": [0.91, 0.06, 0.03]}},
            }
        },
    }


def run_tests() -> None:
    original_predict = agent_main.model_client.predict
    original_geocode = agent_main.geocode_location
    original_weather = agent_main.get_weather
    original_soil = agent_main.get_soil_properties

    try:
        agent_main.model_client.predict = _dummy_model_response

        # Test 1: Direct features path
        r1 = client.post(
            "/recommend",
            json={"N": 90, "P": 42, "K": 43, "temperature": 25.6, "humidity": 71.4, "ph": 6.4},
        )
        assert r1.status_code == 200, r1.text
        b1 = r1.json()
        assert "final_crop" in b1
        assert "provenance" in b1
        assert b1["provenance"]["temperature"]["source"] == "user"

        # Test 2: Location enrichment path
        agent_main.geocode_location = lambda location: {
            "lat": 28.61,
            "lon": 77.20,
            "region": "global",
            "source": "nominatim",
        }
        agent_main.get_weather = lambda lat, lon: {
            "temperature": 30.0,
            "humidity": 65.0,
            "rainfall": 0.0,
            "estimated": True,
            "source": "open_meteo",
        }
        agent_main.get_soil_properties = lambda lat, lon: {
            "ph": 6.7,
            "texture": "unknown",
            "estimated": True,
            "source": "soilgrids",
        }

        r2 = client.post(
            "/recommend",
            json={"location": "Delhi, India", "N": 80, "P": 35, "K": 45},
        )
        assert r2.status_code == 200, r2.text
        b2 = r2.json()
        assert b2["provenance"]["temperature"]["source"] == "weather_api"
        assert b2["provenance"]["ph"]["source"] == "soil_api"

        # Test 3: Missing N/P/K never fabricated
        r3 = client.post(
            "/recommend",
            json={"location": "Delhi, India", "N": 80, "P": 35},
        )
        assert r3.status_code == 400, r3.text
        d3 = r3.json()["detail"]
        assert "missing_features" in d3
        assert "K" in d3["missing_features"]

        print("All agent pipeline tests passed.")
    finally:
        agent_main.model_client.predict = original_predict
        agent_main.geocode_location = original_geocode
        agent_main.get_weather = original_weather
        agent_main.get_soil_properties = original_soil


if __name__ == "__main__":
    run_tests()
