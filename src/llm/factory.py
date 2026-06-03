"""Build LLM clients from AppConfig and provider-specific environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from src.llm.base import BaseLLMClient
from src.llm.mock_llm import MockLLMClient
from src.llm.openai_compatible import OpenAICompatibleClient
from src.llm.provider_registry import (
    get_provider_spec,
    normalize_provider_name,
    supported_provider_names,
)
from src.utils.logger import get_logger


@dataclass(frozen=True)
class LLMRuntimeConfig:
    """Resolved runtime settings for one LLM provider."""

    provider: str
    display_name: str
    api_key: Optional[str]
    api_key_env: Optional[str]
    base_url: Optional[str]
    model: str
    temperature: float
    timeout_seconds: int
    fallback_to_mock: bool


def build_llm_client(config) -> BaseLLMClient:
    """Build a configured LLM client, falling back to MockLLM when allowed."""

    logger = get_logger(__name__)
    runtime = resolve_llm_runtime_config(config)
    if runtime.provider == "mock":
        logger.info("Using MockLLMClient")
        return MockLLMClient()

    if not runtime.api_key:
        message = (
            f"{runtime.api_key_env or 'LLM_API_KEY'} is not configured for "
            f"{runtime.display_name}."
        )
        if runtime.fallback_to_mock:
            logger.warning("%s Falling back to MockLLMClient.", message)
            return MockLLMClient()
        raise ValueError(message)

    logger.info(
        "Using LLM provider=%s model=%s base_url=%s",
        runtime.provider,
        runtime.model,
        runtime.base_url,
    )
    return OpenAICompatibleClient(
        base_url=runtime.base_url or "",
        api_key=runtime.api_key,
        model=runtime.model,
        provider=runtime.provider,
        timeout_seconds=runtime.timeout_seconds,
        temperature=runtime.temperature,
    )


def resolve_llm_runtime_config(config) -> LLMRuntimeConfig:
    """Resolve provider, key, model, and endpoint from config/env."""

    provider = normalize_provider_name(getattr(config, "llm_provider", None))
    fallback_to_mock = _env_bool("LLM_FALLBACK_TO_MOCK", True)
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    timeout_seconds = int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))

    if provider == "mock":
        return LLMRuntimeConfig(
            provider="mock",
            display_name="MockLLM",
            api_key=None,
            api_key_env=None,
            base_url=None,
            model="mock-model",
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            fallback_to_mock=fallback_to_mock,
        )

    spec = get_provider_spec(provider)
    if spec is None:
        supported = ", ".join(supported_provider_names())
        raise ValueError(f"Unsupported LLM_PROVIDER={provider}. Supported: {supported}")

    env_prefix = provider.upper().replace("-", "_")
    api_key_env = os.getenv("LLM_API_KEY_ENV") or spec.env_key
    api_key = (
        os.getenv(api_key_env)
        or getattr(config, "llm_api_key", None)
        or os.getenv("LLM_API_KEY")
    )
    base_url = (
        os.getenv(f"{env_prefix}_BASE_URL")
        or getattr(config, "llm_base_url", None)
        or os.getenv("LLM_BASE_URL")
        or spec.base_url
    )
    model = (
        os.getenv(f"{env_prefix}_MODEL")
        or getattr(config, "llm_model", None)
        or os.getenv("LLM_MODEL")
        or spec.default_model
    )
    if model == "mock-model":
        model = spec.default_model

    return LLMRuntimeConfig(
        provider=provider,
        display_name=spec.display_name,
        api_key=api_key,
        api_key_env=api_key_env,
        base_url=base_url,
        model=model,
        temperature=temperature,
        timeout_seconds=timeout_seconds,
        fallback_to_mock=fallback_to_mock,
    )


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
