"""Search collector skeleton with mock fallback results."""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Iterable, List, Optional

import requests

from src.collectors.base import BaseCollector
from src.models import ArticleRaw
from src.utils.logger import get_logger
from src.utils.time_utils import now_iso
from src.web_access.strategy_router import WebAccessLayer


class SearchCollector(BaseCollector):
    """Collect article candidates from a configurable, compliant search API adapter."""

    def __init__(
        self,
        keywords: Iterable[str],
        provider: str = "mock",
        web_access_layer: Optional[WebAccessLayer] = None,
        site_filter: Optional[str] = None,
        recent_days: int = 7,
        max_results: int = 5,
    ):
        self.keywords = [keyword for keyword in keywords if keyword]
        self.provider = provider or os.getenv("SEARCH_PROVIDER", "mock")
        self.web_access_layer = web_access_layer
        self.site_filter = site_filter
        self.recent_days = recent_days
        self.max_results = max_results
        self.logger = get_logger(__name__)

    def collect(self) -> List[ArticleRaw]:
        """Return search results or mock hints when no authorized API is configured."""

        if self.provider != "mock" and self._has_provider_key():
            self.logger.info("Search provider %s configured; adapter hook reserved.", self.provider)
            candidates = self._collect_from_adapter()
            return self._fetch_candidate_urls(candidates)

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

        if self.provider == "bing":
            return self._collect_from_bing()
        if self.provider == "tavily":
            return self._collect_from_tavily()
        self.logger.info("Adapter for provider %s is not implemented in the MVP.", self.provider)
        return []

    def _collect_from_tavily(self) -> List[ArticleRaw]:
        """Collect search candidates from Tavily Search API."""

        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return []

        candidates: List[ArticleRaw] = []
        seen_urls = set()
        end_date = date.today()
        start_date = end_date - timedelta(days=max(self.recent_days - 1, 0))
        include_domains = self._include_domains()

        for keyword in self.keywords[:5]:
            query = self._build_query(keyword)
            payload = {
                "query": query,
                "search_depth": "basic",
                "topic": "general",
                "max_results": self.max_results,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "include_answer": False,
                "include_raw_content": False,
            }
            if include_domains:
                payload["include_domains"] = include_domains

            try:
                response = requests.post(
                    "https://api.tavily.com/search",
                    json=payload,
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=20,
                )
                response.raise_for_status()
                payload_response = response.json()
            except Exception as exc:  # noqa: BLE001 - adapter should not stop pipeline
                self.logger.warning("Tavily search failed for %s: %s", keyword, exc)
                continue

            for item in payload_response.get("results", []):
                url = item.get("url")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                candidates.append(
                    ArticleRaw(
                        source_type="search_candidate",
                        url=url,
                        title=item.get("title") or url,
                        raw_text=item.get("content") or "",
                        fetched_at=now_iso(),
                        fetch_strategy="tavily_search",
                        fetch_metadata={
                            "strategy": "tavily_search",
                            "query": query,
                            "provider": "tavily",
                            "score": item.get("score"),
                            "published_date": item.get("published_date"),
                            "start_date": start_date.isoformat(),
                            "end_date": end_date.isoformat(),
                        },
                        quality_flags=["search_candidate"],
                    )
                )
        return candidates

    def _collect_from_bing(self) -> List[ArticleRaw]:
        """Collect search candidates from the authorized Bing Web Search API."""

        api_key = os.getenv("BING_SEARCH_API_KEY")
        if not api_key:
            return []

        candidates: List[ArticleRaw] = []
        seen_urls = set()
        freshness = "Day" if self.recent_days <= 1 else "Week" if self.recent_days <= 7 else "Month"

        for keyword in self.keywords[:5]:
            query = self._build_query(keyword)
            try:
                response = requests.get(
                    "https://api.bing.microsoft.com/v7.0/search",
                    params={
                        "q": query,
                        "count": self.max_results,
                        "freshness": freshness,
                        "mkt": "zh-CN",
                        "responseFilter": "Webpages",
                    },
                    headers={"Ocp-Apim-Subscription-Key": api_key},
                    timeout=15,
                )
                response.raise_for_status()
                payload = response.json()
            except Exception as exc:  # noqa: BLE001 - adapter should not stop pipeline
                self.logger.warning("Bing search failed for %s: %s", keyword, exc)
                continue

            for item in payload.get("webPages", {}).get("value", []):
                url = item.get("url")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                candidates.append(
                    ArticleRaw(
                        source_type="search_candidate",
                        url=url,
                        title=item.get("name") or url,
                        raw_text=item.get("snippet") or "",
                        fetched_at=now_iso(),
                        fetch_strategy="bing_search",
                        fetch_metadata={
                            "strategy": "bing_search",
                            "query": query,
                            "freshness": freshness,
                            "provider": "bing",
                        },
                        quality_flags=["search_candidate"],
                    )
                )
        return candidates

    def _build_query(self, keyword: str) -> str:
        """Build a focused search query without brute forcing URL variants."""

        keyword = keyword.strip()
        if self.site_filter:
            return f"site:{self.site_filter} {keyword}"
        return keyword

    def _include_domains(self) -> List[str]:
        """Return provider domain filters derived from site_filter."""

        if not self.site_filter:
            return []
        domain = self.site_filter.split("/", 1)[0].strip()
        return [domain] if domain else []

    def _fetch_candidate_urls(self, candidates: List[ArticleRaw]) -> List[ArticleRaw]:
        """Fetch search result URLs through WebAccessLayer when an adapter provides them."""

        if not self.web_access_layer:
            return candidates

        articles: List[ArticleRaw] = []
        for candidate in candidates:
            if not candidate.url:
                articles.append(candidate)
                continue
            fetched = self.web_access_layer.fetch_article(
                candidate.url,
                source_type="search",
            )
            if fetched.fetch_status != "success":
                self.logger.warning(
                    "Search result fetch failed: %s | %s",
                    candidate.url,
                    fetched.error_message,
                )
            articles.append(fetched)
        return articles

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
