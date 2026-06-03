"""OpenAI-compatible chat completion client."""

from __future__ import annotations

import requests

from src.llm.base import BaseLLMClient


class OpenAICompatibleClient(BaseLLMClient):
    """Call an OpenAI-compatible chat-completions API."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        provider: str = "openai-compatible",
        timeout_seconds: int = 60,
        temperature: float = 0.2,
        system_prompt: str = "You are a precise TMT equity research assistant.",
    ):
        if not api_key:
            raise ValueError("LLM_API_KEY is required for OpenAICompatibleClient")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.provider = provider
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.system_prompt = system_prompt

    def generate(self, prompt: str) -> str:
        """Generate a response via /chat/completions."""

        url = (
            self.base_url
            if self.base_url.endswith("/chat/completions")
            else f"{self.base_url}/chat/completions"
        )
        response = requests.post(
            url,
            timeout=self.timeout_seconds,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": self.system_prompt,
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": self.temperature,
            },
        )
        response.raise_for_status()
        payload = response.json()
        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(
                f"Unexpected response from {self.provider}: {payload}"
            ) from exc
