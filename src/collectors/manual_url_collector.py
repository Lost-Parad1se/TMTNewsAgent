"""Manual URL collector for public article links."""

from __future__ import annotations

from typing import Iterable, List, Optional

from src.collectors.base import BaseCollector
from src.extractors.article_extractor import ArticleExtractor
from src.models import ArticleRaw
from src.utils.logger import get_logger


class ManualURLCollector(BaseCollector):
    """Collect articles from user-provided public URLs."""

    def __init__(
        self,
        urls: Iterable[str],
        extractor: Optional[ArticleExtractor] = None,
        max_urls: int = 20,
    ):
        self.urls = [url for url in urls if url]
        self.extractor = extractor or ArticleExtractor()
        self.max_urls = max_urls
        self.logger = get_logger(__name__)

    def collect(self) -> List[ArticleRaw]:
        """Fetch and parse manually supplied URLs."""

        articles: List[ArticleRaw] = []
        for url in self.urls[: self.max_urls]:
            self.logger.info("Collecting manual URL: %s", url)
            article = self.extractor.fetch_article(url, source_type="manual_url")
            if article.fetch_status != "success":
                self.logger.warning("Manual URL failed: %s | %s", url, article.error_message)
            articles.append(article)
        return articles
