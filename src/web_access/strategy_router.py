"""Strategy routing and orchestration for compliant web access."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Iterable, List, Optional

from src.models import ArticleRaw
from src.utils.time_utils import now_iso
from src.web_access.base import BaseFetcher, FetchResult
from src.web_access.cdp_fetcher import CDPFetcher
from src.web_access.jina_fetcher import JinaFetcher
from src.web_access.static_fetcher import StaticFetcher
from src.web_access.validators import is_pdf_url, is_probably_url, is_wechat_url


class AccessStrategyRouter:
    """Choose a conservative fetch strategy sequence for one URL."""

    def route(
        self,
        url: Optional[str],
        source_type: Optional[str] = None,
        config: Optional[Any] = None,
        previous_error: Optional[str] = None,
    ) -> List[str]:
        """Return ordered strategy names for one URL."""

        del source_type, previous_error
        if not url or not is_probably_url(url):
            return []

        forced_strategy = _cfg_get(config, "strategy", "auto")
        if forced_strategy and forced_strategy != "auto":
            return self._forced_strategy(forced_strategy, config)

        if is_pdf_url(url):
            return ["static"]

        if is_wechat_url(url):
            strategies = ["static"]
            if _cfg_get(config, "enable_cdp", False):
                strategies.append("cdp_optional")
                strategies.append("manual")
            else:
                strategies.append("manual_required")
            return strategies

        return ["jina", "static"]

    def _forced_strategy(self, strategy: str, config: Optional[Any]) -> List[str]:
        normalized = (strategy or "auto").lower()
        if normalized == "static":
            return ["static"]
        if normalized == "jina":
            return ["jina"]
        if normalized == "cdp":
            return ["cdp_optional"] if _cfg_get(config, "enable_cdp", False) else [
                "manual_required"
            ]
        if normalized == "manual":
            return ["manual_required"]
        return ["jina", "static"]


class WebAccessLayer:
    """Low-intrusion facade that turns FetchResult objects into ArticleRaw items."""

    def __init__(
        self,
        config: Optional[Any] = None,
        router: Optional[AccessStrategyRouter] = None,
        fetchers: Optional[Dict[str, BaseFetcher]] = None,
    ):
        self.config = config
        self.router = router or AccessStrategyRouter()
        timeout_seconds = int(_cfg_get(config, "timeout_seconds", 15))
        user_agent = _cfg_get(
            config,
            "user_agent",
            "TMTNewsAgent/0.1 (+public information research prototype)",
        )
        self.fetchers = fetchers or {
            "static": StaticFetcher(timeout_seconds=timeout_seconds, user_agent=user_agent),
            "jina": JinaFetcher(
                timeout_seconds=int(_cfg_get(config, "jina_timeout_seconds", 20)),
                base_url=_cfg_get(config, "jina_base_url", "https://r.jina.ai/"),
                user_agent=user_agent,
            ),
            "cdp_optional": CDPFetcher(
                enable_cdp=bool(_cfg_get(config, "enable_cdp", False)),
                proxy_url=_cfg_get(config, "cdp_proxy_url", "http://localhost:3456"),
                timeout_seconds=timeout_seconds,
            ),
        }

    def fetch(
        self,
        url: str,
        source_type: str = "manual_url",
        previous_error: Optional[str] = None,
    ) -> FetchResult:
        """Fetch one URL using the configured strategy sequence."""

        strategies = self.router.route(
            url=url,
            source_type=source_type,
            config=self.config,
            previous_error=previous_error,
        )
        if not strategies:
            return self._manual_required(
                url,
                "No URL strategy selected. Keyword search should be handled by SearchCollector.",
            )

        failures: List[Dict[str, Any]] = []
        for strategy in strategies:
            if strategy in {"manual", "manual_required"}:
                return self._manual_required(url, "Manual text paste or CSV fallback required.")
            fetcher = self.fetchers.get(strategy)
            if fetcher is None:
                failures.append({"strategy": strategy, "error": "fetcher not configured"})
                continue
            result = fetcher.fetch(url)
            if result.status == "success":
                return result
            failures.append(
                {
                    "strategy": result.strategy,
                    "status": result.status,
                    "error": result.error,
                }
            )
            if result.status == "manual_required":
                continue

        return FetchResult(
            url=url,
            strategy=strategies[-1],
            status="failed",
            title=url,
            error="All web access strategies failed or required manual fallback.",
            metadata={"strategy_attempts": failures},
        )

    def fetch_article(self, url: str, source_type: str = "manual_url") -> ArticleRaw:
        """Fetch one URL and adapt the result into the project's ArticleRaw model."""

        return fetch_result_to_article(self.fetch(url, source_type=source_type), source_type)

    def fetch_many(
        self,
        urls: Iterable[str],
        source_type: str = "manual_url",
    ) -> List[ArticleRaw]:
        """Fetch URLs with conservative optional low concurrency."""

        url_list = [url for url in urls if url]
        max_concurrency = int(_cfg_get(self.config, "max_concurrency", 1))
        if max_concurrency <= 1 or len(url_list) <= 1:
            return [self.fetch_article(url, source_type=source_type) for url in url_list]

        workers = min(max_concurrency, 4, len(url_list))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            return list(
                executor.map(
                    lambda item: self.fetch_article(item, source_type=source_type),
                    url_list,
                )
            )

    @staticmethod
    def summarize_results(articles: Iterable[ArticleRaw]) -> Dict[str, Any]:
        """Build report counters from ArticleRaw fetch metadata."""

        strategy_counts: Counter[str] = Counter()
        cdp_used_count = 0
        manual_required_count = 0
        failed_fetch_items: List[Dict[str, Any]] = []

        for article in articles:
            strategy = article.fetch_strategy or article.fetch_metadata.get("strategy")
            if strategy:
                strategy_counts[str(strategy)] += 1
            if article.fetch_metadata.get("cdp_used") or strategy == "cdp":
                cdp_used_count += 1
            if article.fetch_status == "manual_required":
                manual_required_count += 1
            if article.fetch_status in {"failed", "partial", "manual_required"}:
                failed_fetch_items.append(
                    {
                        "title": article.title,
                        "url": article.url,
                        "status": article.fetch_status,
                        "strategy": strategy,
                        "error": article.error_message,
                    }
                )

        return {
            "fetch_strategy_stats": dict(strategy_counts),
            "cdp_used_count": cdp_used_count,
            "manual_required_count": manual_required_count,
            "failed_fetch_items": failed_fetch_items,
        }

    def _manual_required(self, url: str, error: str) -> FetchResult:
        return FetchResult(
            url=url,
            strategy="manual_required",
            status="manual_required",
            title=url,
            error=error,
            metadata={"manual_fallback": "paste_text_or_csv"},
        )


def fetch_result_to_article(result: FetchResult, source_type: str) -> ArticleRaw:
    """Convert a FetchResult to ArticleRaw without dropping strategy metadata."""

    quality_flags = ["web_access", f"strategy:{result.strategy}"]
    if result.status != "success":
        quality_flags.append(result.status)
    raw_text = result.text or result.markdown
    return ArticleRaw(
        source_type=source_type,
        url=result.url,
        final_url=result.final_url,
        title=result.title or result.final_url or result.url,
        raw_html=result.html,
        raw_text=raw_text,
        fetched_at=result.fetched_at or now_iso(),
        fetch_status=result.status,
        fetch_strategy=result.strategy,
        fetch_metadata={"strategy": result.strategy, **result.metadata},
        error_message=result.error,
        quality_flags=quality_flags,
    )


def _cfg_get(config: Optional[Any], key: str, default: Any = None) -> Any:
    """Read config values from Pydantic models or dictionaries."""

    if config is None:
        return default
    if isinstance(config, dict):
        return config.get(key, default)
    nested = getattr(config, "web_access", None)
    if isinstance(nested, dict) and key in nested:
        return nested[key]
    return getattr(config, key, default)
