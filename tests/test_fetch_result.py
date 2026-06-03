"""Tests for FetchResult adaptation and failure handling."""

import unittest

from src.web_access.base import BaseFetcher, FetchResult
from src.web_access.jina_fetcher import normalize_jina_url
from src.web_access.strategy_router import WebAccessLayer, fetch_result_to_article


class FailingFetcher(BaseFetcher):
    """Fetcher that always returns a failed item instead of raising."""

    strategy_name = "static"

    def fetch(self, url: str) -> FetchResult:
        return FetchResult(
            url=url,
            strategy=self.strategy_name,
            status="failed",
            error="network unavailable",
        )


class FetchResultTest(unittest.TestCase):
    """Validate fetch result behavior."""

    def test_failed_fetch_result_becomes_failed_article(self):
        result = FetchResult(
            url="https://example.com/a",
            strategy="static",
            status="failed",
            error="HTTP 500",
        )

        article = fetch_result_to_article(result, "manual_url")

        self.assertEqual("failed", article.fetch_status)
        self.assertEqual("static", article.fetch_strategy)
        self.assertEqual("HTTP 500", article.error_message)

    def test_failed_fetch_does_not_raise_or_break_collection(self):
        layer = WebAccessLayer(
            config={"strategy": "static"},
            fetchers={"static": FailingFetcher()},
        )

        article = layer.fetch_article("https://example.com/a", source_type="manual_url")

        self.assertEqual("failed", article.fetch_status)
        self.assertIn("strategy_attempts", article.fetch_metadata)

    def test_jina_url_normalization_does_not_duplicate_prefix(self):
        jina_url = "https://r.jina.ai/https://example.com/path?q=1"

        self.assertEqual(jina_url, normalize_jina_url(jina_url))
        self.assertEqual(
            "https://r.jina.ai/https://example.com/path?q=1",
            normalize_jina_url("https://example.com/path?q=1"),
        )


if __name__ == "__main__":
    unittest.main()
