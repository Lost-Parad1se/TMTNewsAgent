"""Tests for research brief Markdown generation."""

import unittest

from src.models import ArticleProcessed
from src.processors.report_writer import ReportWriter


class ReportWriterTest(unittest.TestCase):
    """Validate Markdown brief generation."""

    def test_markdown_can_be_generated(self):
        """A minimal processed article should render into the expected sections."""

        article = ArticleProcessed(
            article_id="abc123",
            url="https://example.com/mock",
            title="[mock] AI算力订单释放",
            account_name="mock公众号",
            publish_time="2026-06-01",
            clean_text="mock text",
            summary="AI算力链条出现订单线索，需进一步验证。",
            industry_tags=["AI算力"],
            company_tags=["腾讯控股"],
            topic_tags=["AI算力", "订单"],
            importance_score=7.0,
            sentiment="neutral",
            investment_implications=["关注订单交付和收入确认。"],
            risks=["信息真实性需进一步验证。"],
        )
        writer = ReportWriter()
        brief = writer.build_brief([article], topic="AI算力", date="2026-06-01")
        markdown = writer.to_markdown(brief)
        self.assertIn("# TMT/互联网公众号新闻投研简报", markdown)
        self.assertIn("## 二、重点新闻", markdown)
        self.assertIn("腾讯控股", markdown)


if __name__ == "__main__":
    unittest.main()
