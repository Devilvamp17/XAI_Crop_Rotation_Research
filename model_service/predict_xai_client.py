from __future__ import annotations

from typing import Any

import httpx


class PredictXAIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def predict(
        self,
        features: dict[str, float],
        models: list[str] | None = None,
        top_k: int = 3,
    ) -> dict[str, Any]:
        payload = {
            "input": features,
            "models": models or ["xgboost", "random_forest", "logistic_regression"],
            "top_k": top_k,
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/predict", json=payload)
            response.raise_for_status()
            return response.json()
