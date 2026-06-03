"""Rule-based industry and topic classification for TMT articles."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from src.models import ClassificationResult


class RuleBasedClassifier:
    """Classify articles by keyword rules, with room for optional LLM refinement."""

    def __init__(
        self,
        industry_topics: Dict[str, Dict[str, Iterable[str]]] | None = None,
        importance_keywords: Dict[str, Iterable[str]] | None = None,
    ):
        self.industry_topics = industry_topics or {}
        self.importance_keywords = importance_keywords or {}

    def classify(
        self,
        title: str,
        text: str,
        company_tags: List[str] | None = None,
        account_name: str | None = None,
    ) -> ClassificationResult:
        """Return industry tags, topic tags, and an importance score."""

        haystack = f"{title}\n{text}".lower()
        industry_tags = self._match_industry_tags(haystack)
        topic_tags = self._match_topic_tags(haystack, industry_tags)
        importance_score = self._score_importance(
            haystack=haystack,
            company_tags=company_tags or [],
            industry_tags=industry_tags,
            account_name=account_name,
        )
        return ClassificationResult(
            industry_tags=industry_tags,
            topic_tags=topic_tags,
            importance_score=importance_score,
        )

    def _match_industry_tags(self, haystack: str) -> List[str]:
        """Match industry categories from configured keyword dictionaries."""

        tags: List[str] = []
        for topic, config in self.industry_topics.items():
            keywords = config.get("keywords", []) if isinstance(config, dict) else []
            if any(keyword.lower() in haystack for keyword in keywords):
                tags.append(topic)
        return tags

    def _match_topic_tags(self, haystack: str, industry_tags: List[str]) -> List[str]:
        """Create more specific topic tags from matched keywords."""

        tags = list(industry_tags)
        for word in self.importance_keywords.get("high", []):
            if word.lower() in haystack and word not in tags:
                tags.append(word)
        return tags[:8]

    def _score_importance(
        self,
        haystack: str,
        company_tags: List[str],
        industry_tags: List[str],
        account_name: str | None,
    ) -> float:
        """Score article importance using transparent research-oriented rules."""

        score = 2.0
        if company_tags:
            score += min(2.0, len(company_tags) * 0.8)
        if industry_tags:
            score += min(1.5, len(industry_tags) * 0.5)
        for word in self.importance_keywords.get("high", []):
            if word.lower() in haystack:
                score += 0.7
        for word in self.importance_keywords.get("medium", []):
            if word.lower() in haystack:
                score += 0.35
        if account_name and any(token in account_name for token in ["证券", "研究", "财经"]):
            score += 0.5
        return round(min(score, 10.0), 2)


def build_classifier_from_config(topics_config: Dict[str, Any]) -> RuleBasedClassifier:
    """Create a classifier from topics.yaml content."""

    return RuleBasedClassifier(
        industry_topics=topics_config.get("industry_topics", {}),
        importance_keywords=topics_config.get("importance_keywords", {}),
    )
