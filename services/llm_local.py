from __future__ import annotations

import time
from typing import Any

import httpx

from core import settings


class LocalLLMClient:
    def __init__(self) -> None:
        raw_provider = settings.llm_provider.lower().strip()
        provider_aliases = {"local": "ollama"}
        self.provider = provider_aliases.get(raw_provider, raw_provider)
        if self.provider == "openrouter":
            self.base_url = settings.openrouter_base_url.rstrip("/")
            self.model = settings.openrouter_model
        elif self.provider == "openai":
            self.base_url = settings.openai_base_url.rstrip("/")
            self.model = settings.openai_model
        else:
            self.base_url = settings.local_llm_base_url.rstrip("/")
            self.model = settings.local_llm_model
        self.temperature = settings.local_llm_temperature
        self.max_tokens = settings.local_llm_max_tokens
        self.timeout_seconds = settings.local_llm_timeout_seconds

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        if self.provider in {"openrouter", "openai"}:
            if self.provider == "openrouter":
                api_key = settings.openrouter_api_key
                referer = settings.openrouter_http_referer
                x_title = settings.openrouter_x_title
            else:
                api_key = settings.openai_api_key
                referer = ""
                x_title = ""

            if not api_key:
                raise ValueError(f"{self.provider.upper()} API key is missing in environment.")

            payload: dict[str, Any] = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
            }
            if self.provider == "openrouter":
                headers["HTTP-Referer"] = referer
                headers["X-Title"] = x_title

            data: dict[str, Any] | None = None
            with httpx.Client(timeout=self.timeout_seconds) as client:
                for attempt in range(3):
                    response = client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                    if response.status_code != 429:
                        response.raise_for_status()
                        data = response.json()
                        break
                    if attempt < 2:
                        time.sleep(2**attempt)
                if data is None:
                    raise ValueError(f"{self.provider} rate-limited requests (429). Try again shortly.")

            choices = data.get("choices", [])
            if not choices:
                raise ValueError(f"No choices returned by {self.provider}.")
            message = choices[0].get("message", {})
            content = message.get("content")

            if isinstance(content, str) and content.strip():
                return content.strip()

            if isinstance(content, list):
                parts: list[str] = []
                for item in content:
                    if isinstance(item, dict):
                        text = item.get("text")
                        if isinstance(text, str) and text.strip():
                            parts.append(text.strip())
                if parts:
                    return "\n".join(parts)

            reasoning = message.get("reasoning")
            if isinstance(reasoning, str) and reasoning.strip():
                return reasoning.strip()

            refusal = message.get("refusal")
            if isinstance(refusal, str) and refusal.strip():
                raise ValueError(f"Model refusal: {refusal.strip()}")

            raise ValueError(f"Empty response content from {self.provider}.")

        if self.provider != "ollama":
            raise ValueError("Unsupported LLM provider. Use 'local', 'openrouter', or 'openai'.")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

        message = data.get("message", {})
        content = message.get("content", "")
        if not content:
            raise ValueError("Empty response from local LLM")
        return content

    def healthcheck(self) -> dict[str, Any]:
        if self.provider in {"openrouter", "openai"}:
            if self.provider == "openrouter":
                api_key = settings.openrouter_api_key
                base_url = settings.openrouter_base_url.rstrip("/")
                missing_message = "OPENROUTER_API_KEY is missing"
            else:
                api_key = settings.openai_api_key
                base_url = settings.openai_base_url.rstrip("/")
                missing_message = "OPENAI_API_KEY is missing"

            if not api_key:
                return {
                    "provider": self.provider,
                    "base_url": base_url,
                    "configured_model": self.model,
                    "available_models": [],
                    "configured_model_available": False,
                    "error": missing_message,
                }
            headers = {"Authorization": f"Bearer {api_key}"}
            with httpx.Client(timeout=15.0) as client:
                response = client.get(f"{base_url}/models", headers=headers)
                response.raise_for_status()
                data = response.json()
            models = [m.get("id", "") for m in data.get("data", [])]
        else:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]

        return {
            "provider": self.provider,
            "base_url": self.base_url,
            "configured_model": self.model,
            "available_models": models,
            "configured_model_available": self.model in models,
        }
