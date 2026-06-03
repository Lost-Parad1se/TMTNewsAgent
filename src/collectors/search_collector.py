"""Search collector skeleton with mock fallback results."""

from __future__ import annotations

import os
from typing import Iterable, List

from src.collectors.base import BaseCollector
from src.models import ArticleRaw
from src.utils.logger import get_logger
from src.utils.time_utils import now_iso


class SearchCollector(BaseCollector):
    """Collect article candidates from a configurable, compliant search API adapter."""

    def __init__(self, keywords: Iterable[str], provider: str = "mock"):
        self.keywords = [keyword for keyword in keywords if keyword]
        self.provider = provider or os.getenv("SEARCH_PROVIDER", "mock")
        self.logger = get_logger(__name__)

    def collect(self) -> List[ArticleRaw]:
        """Return search results or mock hints when no authorized API is configured."""

        if self.provider != "mock" and self._has_provider_key():
            self.logger.info("Search provider %s configured; adapter hook reserved.", self.provider)
            return self._collect_from_adapter()

        self.logger.warning(
            "No authorized search API configured; returning mock search results. "
            "Use CSV or manual_url mode for real public links."
        )
        return self._mock_results()

    def _has_provider_key(self) -> bool:
        """Check whether a configured provider has an API key in the environment."""

        provider_key = {
            "tavily": "TAVILY_API_KEY",
            "serpapi": "SERPAPI_API_KEY",
            "bing": "BING_SEARCH_API_KEY",
            "sogou_wechat": "SOGOU_WECHAT_API_KEY",
        }.get(self.provider)
        return bool(provider_key and os.getenv(provider_key))

    def _collect_from_adapter(self) -> List[ArticleRaw]:
        """Placeholder for compliant third-party search adapters."""

        self.logger.info("Adapter for provider %s is not implemented in the MVP.", self.provider)
        return []

    def _mock_results(self) -> List[ArticleRaw]:
        """Create mock search results that explain the fallback path."""

        articles: List[ArticleRaw] = []
        for keyword in self.keywords[:5]:
            articles.append(
                ArticleRaw(
                    source_type="search_mock",
                    url=None,
                    title=f"[mock] {keyword} 相关公开文章线索",
                    account_name="mock-search",
                    raw_text=(
                        f"mock 数据：这是围绕“{keyword}”生成的搜索占位结果。"
                        "实际生产环境应接入合法授权的搜索 API 或第三方数据服务，"
                        "并遵守平台访问规则。"
                    ),
                    fetched_at=now_iso(),
                    quality_flags=["mock"],
                )
            )
        return articles
