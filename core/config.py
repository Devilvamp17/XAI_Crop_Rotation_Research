from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    model_api_base_url: str = os.getenv("MODEL_API_BASE_URL", "http://127.0.0.1:8000")

    nominatim_url: str = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org/search")
    nominatim_user_agent: str = os.getenv(
        "NOMINATIM_USER_AGENT",
        "xai-crop-rotation-research/1.0 (contact: local-dev)",
    )
    open_meteo_url: str = os.getenv("OPEN_METEO_URL", "https://api.open-meteo.com/v1/forecast")
    soilgrids_url: str = os.getenv(
        "SOILGRIDS_URL", "https://rest.isric.org/soilgrids/v2.0/properties/query"
    )

    # Placeholder keys for future providers; free endpoints currently do not require them.
    weather_api_key: str = os.getenv("WEATHER_API_KEY", "")
    soil_api_key: str = os.getenv("SOIL_API_KEY", "")
    geocode_api_key: str = os.getenv("GEOCODE_API_KEY", "")

    llm_provider: str = os.getenv("LLM_PROVIDER", os.getenv("LOCAL_LLM_PROVIDER", "local"))
    local_llm_base_url: str = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:11434")
    local_llm_model: str = os.getenv("LOCAL_LLM_MODEL", "llama3.2:3b")
    local_llm_temperature: float = float(os.getenv("LOCAL_LLM_TEMPERATURE", "0.2"))
    local_llm_max_tokens: int = int(os.getenv("LOCAL_LLM_MAX_TOKENS", "512"))
    local_llm_timeout_seconds: float = float(os.getenv("LOCAL_LLM_TIMEOUT_SECONDS", "180"))

    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_model: str = os.getenv(
        "OPENROUTER_MODEL", "openrouter/free"
    )
    openrouter_http_referer: str = os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost")
    openrouter_x_title: str = os.getenv("OPENROUTER_X_TITLE", "xai-crop-rotation-research")


settings = Settings()
