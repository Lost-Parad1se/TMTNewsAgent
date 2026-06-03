"""Tests for provider-aware LLM factory configuration."""

import os
import unittest
from unittest.mock import patch

from src.config import AppConfig
from src.llm.factory import build_llm_client, resolve_llm_runtime_config
from src.llm.mock_llm import MockLLMClient
from src.llm.openai_compatible import OpenAICompatibleClient


class LLMFactoryTest(unittest.TestCase):
    """Validate provider resolution without calling external APIs."""

    def _config(self, provider: str) -> AppConfig:
        return AppConfig(
            project_root=".",
            llm_provider=provider,
            sqlite_path="data/processed/tmt_news_agent.db",
            output_dir="data/outputs",
        )

    def test_gemini_defaults_are_resolved(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "key"}, clear=True):
            runtime = resolve_llm_runtime_config(self._config("gemini"))

        self.assertEqual("gemini", runtime.provider)
        self.assertEqual("GEMINI_API_KEY", runtime.api_key_env)
        self.assertEqual("gemini-2.5-flash", runtime.model)
        self.assertEqual(
            "https://generativelanguage.googleapis.com/v1beta/openai",
            runtime.base_url,
        )

    def test_qwen_deepseek_and_glm_defaults_are_resolved(self):
        cases = [
            ("qwen", "DASHSCOPE_API_KEY", "qwen-plus"),
            ("deepseek", "DEEPSEEK_API_KEY", "deepseek-v4-flash"),
            ("glm", "ZHIPUAI_API_KEY", "glm-5.1"),
        ]
        for provider, env_key, model in cases:
            with self.subTest(provider=provider):
                with patch.dict(os.environ, {env_key: "key"}, clear=True):
                    runtime = resolve_llm_runtime_config(self._config(provider))
                self.assertEqual(env_key, runtime.api_key_env)
                self.assertEqual(model, runtime.model)

    def test_missing_key_falls_back_to_mock_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            client = build_llm_client(self._config("gemini"))

        self.assertIsInstance(client, MockLLMClient)

    def test_configured_provider_builds_openai_compatible_client(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "key"}, clear=True):
            client = build_llm_client(self._config("deepseek"))

        self.assertIsInstance(client, OpenAICompatibleClient)
        self.assertEqual("deepseek", client.provider)


if __name__ == "__main__":
    unittest.main()
