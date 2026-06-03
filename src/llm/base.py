"""Base interface for replaceable LLM clients."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """Minimal LLM client contract."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate text from a prompt."""
