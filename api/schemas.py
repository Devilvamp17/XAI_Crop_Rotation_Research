from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FeatureValue(BaseModel):
    value: float
    source: str


class AgentRequest(BaseModel):
    location: str | None = None
    region: str | None = None
    month: int | None = Field(default=None, ge=1, le=12)

    N: float | None = None
    P: float | None = None
    K: float | None = None
    temperature: float | None = None
    humidity: float | None = None
    ph: float | None = None

    models: list[str] = Field(default_factory=lambda: ["xgboost", "random_forest", "logistic_regression"])
    top_k: int = Field(default=3, ge=1, le=10)


class AgentResponse(BaseModel):
    final_crop: str
    confidence: float
    raw_model_confidence: float
    calendar_suitability: float
    adjusted_confidence: float
    eps: float
    top3: list[dict[str, Any]]
    shap: dict[str, Any]
    lime: dict[str, Any]
    curves: dict[str, Any]
    llm_curves: dict[str, Any]
    xai_eval: dict[str, Any]
    calendar_adjustment: dict[str, Any]
    provenance: dict[str, FeatureValue]
    tool_calls: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class LLMAdvisoryRequest(BaseModel):
    query: str = Field(..., description="User's natural-language question")
    recommendation_input: AgentRequest


class LLMAdvisoryResponse(BaseModel):
    recommendation: AgentResponse
    llm_response: str
