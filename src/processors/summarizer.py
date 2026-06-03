"""Single-article LLM summarization and JSON normalization."""

from __future__ import annotations

import json
import re
from typing import Any, Dict

from src.llm.base import BaseLLMClient
from src.models import SummaryResult
from src.utils.text_utils import truncate_text


class ArticleSummarizer:
    """Summarize one article into research-assistant style fields."""

    def __init__(self, llm_client: BaseLLMClient, prompt_template: str):
        self.llm_client = llm_client
        self.prompt_template = prompt_template

    def summarize(self, title: str, text: str, account_name: str | None = None) -> SummaryResult:
        """Generate and parse a structured article summary."""

        prompt = (
            self.prompt_template.replace("{title}", title)
            .replace("{account_name}", account_name or "")
            .replace("{text}", truncate_text(text, 5000))
        )
        response = self.llm_client.generate(prompt)
        payload = self._parse_json(response)
        return SummaryResult(**payload)

    def _parse_json(self, response: str) -> Dict[str, Any]:
        """Parse model JSON, tolerating surrounding prose or code fences."""

        cleaned = response.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.S)
            if match:
                return json.loads(match.group(0))
        return {
            "one_sentence_summary": cleaned[:200],
            "key_points": [],
            "related_companies": [],
            "related_topics": [],
            "investment_implications": [],
            "risks": ["LLM 输出未能解析为 JSON，需人工复核。"],
            "importance_score": 0,
            "sentiment": "neutral",
        }
