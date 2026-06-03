"""Tests for classifier and entity mapper."""

import unittest

from src.config import load_config
from src.processors.classifier import build_classifier_from_config
from src.processors.entity_mapper import EntityMapper


class ClassifierTest(unittest.TestCase):
    """Validate company mapping and topic classification."""

    @classmethod
    def setUpClass(cls):
        """Load project config once for all tests."""

        cls.config = load_config()

    def test_company_aliases_are_mapped(self):
        """Tencent, Alibaba, and Meituan aliases should map to canonical names."""

        mapper = EntityMapper(self.config.topics["company_aliases"])
        companies = mapper.map_companies(
            "腾讯与阿里云关注AI算力",
            "美团在本地生活广告投放上加大投入。",
        )
        self.assertIn("腾讯控股", companies)
        self.assertIn("阿里巴巴", companies)
        self.assertIn("美团", companies)

    def test_topic_classification_outputs_tags(self):
        """Classifier should return industry tags and an importance score."""

        classifier = build_classifier_from_config(self.config.topics)
        result = classifier.classify(
            title="AI算力订单与云计算价格调整",
            text="GPU服务器、云厂商价格调整和大模型应用需求提升。",
            company_tags=["腾讯控股"],
        )
        self.assertIn("AI算力", result.industry_tags)
        self.assertIn("云计算", result.industry_tags)
        self.assertGreater(result.importance_score, 3)


if __name__ == "__main__":
    unittest.main()
