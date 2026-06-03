"""Tests for article deduplication."""

import unittest

from src.models import ArticleRaw
from src.processors.deduplicator import Deduplicator
from src.utils.time_utils import now_iso


class DeduplicatorTest(unittest.TestCase):
    """Validate exact and normalized title duplicate detection."""

    def test_duplicate_title_is_detected(self):
        """Titles that normalize to the same value should deduplicate."""

        articles = [
            ArticleRaw(
                source_type="csv",
                url="https://example.com/a",
                title="AI算力订单释放",
                raw_text="mock text one",
                fetched_at=now_iso(),
            ),
            ArticleRaw(
                source_type="csv",
                url="https://example.com/b",
                title="【原创】AI算力订单释放",
                raw_text="mock text two",
                fetched_at=now_iso(),
            ),
        ]
        result = Deduplicator().deduplicate(articles)
        self.assertEqual(len(result.unique_articles), 1)
        self.assertEqual(result.dedup_report["duplicate_count"], 1)


if __name__ == "__main__":
    unittest.main()
