"""Provider defaults for OpenAI-compatible LLM backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class LLMProviderSpec:
    """Static provider settings used by the LLM factory."""

    name: str
    display_name: str
    env_key: str
    base_url: str
    default_model: str
    notes: str = ""


PROVIDER_SPECS: Dict[str, LLMProviderSpec] = {
    "gemini": LLMProviderSpec(
        name="gemini",
        display_name="Google Gemini",
        env_key="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        default_model="gemini-2.5-flash",
        notes="Google AI Studio OpenAI-compatible endpoint.",
    ),
    "qwen": LLMProviderSpec(
        name="qwen",
        display_name="Alibaba Qwen / DashScope",
        env_key="DASHSCOPE_API_KEY",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        default_model="qwen-plus",
        notes="阿里云百炼北京地域 OpenAI 兼容接口。",
    ),
    "deepseek": LLMProviderSpec(
        name="deepseek",
        display_name="DeepSeek",
        env_key="DEEPSEEK_API_KEY",
        base_url="https://api.deepseek.com",
        default_model="deepseek-v4-flash",
        notes="DeepSeek OpenAI-compatible endpoint.",
    ),
    "glm": LLMProviderSpec(
        name="glm",
        display_name="Zhipu GLM",
        env_key="ZHIPUAI_API_KEY",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        default_model="glm-5.1",
        notes="智谱 AI OpenAI 兼容接口。",
    ),
    "kimi": LLMProviderSpec(
        name="kimi",
        display_name="Kimi / Moonshot",
        env_key="MOONSHOT_API_KEY",
        base_url="https://api.moonshot.cn/v1",
        default_model="moonshot-v1-8k",
        notes="月之暗面 Kimi OpenAI 兼容接口。",
    ),
    "openai-compatible": LLMProviderSpec(
        name="openai-compatible",
        display_name="Custom OpenAI-compatible",
        env_key="LLM_API_KEY",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
        notes="Generic provider configured by LLM_BASE_URL / LLM_API_KEY / LLM_MODEL.",
    ),
}


ALIASES = {
    "mock": "mock",
    "openai": "openai-compatible",
    "custom": "openai-compatible",
    "qwen-plus": "qwen",
    "dashscope": "qwen",
    "deepseek-ai": "deepseek",
    "zhipu": "glm",
    "zhipuai": "glm",
    "bigmodel": "glm",
    "moonshot": "kimi",
    "moonshot-ai": "kimi",
    "moonshotai": "kimi",
}


def normalize_provider_name(provider: Optional[str]) -> str:
    """Normalize provider names and aliases to registry keys."""

    name = (provider or "mock").strip().lower().replace("_", "-")
    return ALIASES.get(name, name)


def get_provider_spec(provider: str) -> Optional[LLMProviderSpec]:
    """Return a provider spec, or None for mock/unknown providers."""

    return PROVIDER_SPECS.get(normalize_provider_name(provider))


def supported_provider_names() -> list[str]:
    """Return provider names suitable for CLI/API docs."""

    return ["mock", *sorted(PROVIDER_SPECS.keys())]
