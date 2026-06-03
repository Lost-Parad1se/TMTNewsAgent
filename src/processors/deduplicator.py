"""Article deduplication based on URL, normalized title, and text similarity."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

from src.utils.text_utils import normalize_title, simple_similarity


@dataclass
class DeduplicationOutput:
    """Deduplication result with unique articles and diagnostic details."""

    unique_articles: List[Any]
    duplicate_groups: List[List[int]] = field(default_factory=list)
    dedup_report: Dict[str, Any] = field(default_factory=dict)


class Deduplicator:
    """Remove exact and near-duplicate articles."""

    def __init__(self, title_similarity_threshold: float = 0.9):
        self.title_similarity_threshold = title_similarity_threshold

    def deduplicate(self, articles: Sequence[Any]) -> DeduplicationOutput:
        """Return unique articles and duplicate groups."""

        unique_articles: List[Any] = []
        duplicate_groups: List[List[int]] = []
        original_to_unique: Dict[int, int] = {}

        for index, article in enumerate(articles):
            duplicate_of = self._find_duplicate_index(article, unique_articles)
            if duplicate_of is None:
                original_to_unique[index] = len(unique_articles)
                unique_articles.append(article)
                continue

            group = self._get_or_create_group(duplicate_groups, duplicate_of)
            group.append(index)

        report = {
            "input_count": len(articles),
            "unique_count": len(unique_articles),
            "duplicate_count": len(articles) - len(unique_articles),
            "title_similarity_threshold": self.title_similarity_threshold,
        }
        return DeduplicationOutput(unique_articles, duplicate_groups, report)

    def _find_duplicate_index(self, article: Any, unique_articles: Sequence[Any]) -> int | None:
        """Find the unique article index that duplicates the candidate."""

        url = getattr(article, "url", None)
        title = getattr(article, "title", "")
        normalized = normalize_title(title)

        for unique_index, unique in enumerate(unique_articles):
            unique_url = getattr(unique, "url", None)
            unique_title = getattr(unique, "title", "")
            if url and unique_url and url == unique_url:
                return unique_index
            if normalized and normalized == normalize_title(unique_title):
                return unique_index
            if simple_similarity(title, unique_title) > self.title_similarity_threshold:
                return unique_index
        return None

    @staticmethod
    def _get_or_create_group(groups: List[List[int]], duplicate_of: int) -> List[int]:
        """Return an existing duplicate group or create one."""

        for group in groups:
            if duplicate_of in group:
                return group
        group = [duplicate_of]
        groups.append(group)
        return group
