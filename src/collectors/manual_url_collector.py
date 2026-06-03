"""Manual URL collector for public article links."""

from __future__ import annotations

from typing import Iterable, List, Optional

from src.collectors.base import BaseCollector
from src.models import ArticleRaw
from src.utils.logger import get_logger
from src.web_access.strategy_router import WebAccessLayer


class ManualURLCollector(BaseCollector):
    """Collect articles from user-provided public URLs."""

    def __init__(
        self,
        urls: Iterable[str],
        web_access_layer: Optional[WebAccessLayer] = None,
        max_urls: int = 20,
    ):
        self.urls = [url for url in urls if url]
        self.web_access_layer = web_access_layer or WebAccessLayer()
        self.max_urls = max_urls
        self.logger = get_logger(__name__)

    def collect(self) -> List[ArticleRaw]:
        """Fetch and parse manually supplied URLs."""

        urls = self.urls[: self.max_urls]
        articles = self.web_access_layer.fetch_many(urls, source_type="manual_url")
        for url, article in zip(urls, articles):
            self.logger.info("Collecting manual URL: %s", url)
            if article.fetch_status != "success":
                self.logger.warning("Manual URL failed: %s | %s", url, article.error_message)
        return articles
