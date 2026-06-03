"""Tests for WebAccessLayer strategy routing."""

import unittest

from src.web_access.base import BaseFetcher, FetchResult
from src.web_access.strategy_router import AccessStrategyRouter, WebAccessLayer


class DummyFetcher(BaseFetcher):
    """Test fetcher that records calls."""

    def __init__(self, strategy: str, status: str = "success"):
        self.strategy_name = strategy
        self.status = status
        self.calls = []

    def fetch(self, url: str) -> FetchResult:
        self.calls.append(url)
        return FetchResult(
            url=url,
            strategy=self.strategy_name,
            status=self.status,
            title="dummy",
            text="dummy text" if self.status == "success" else None,
            error=None if self.status == "success" else "failed",
        )


class StrategyRouterTest(unittest.TestCase):
    """Validate conservative web access routing."""

    def test_wechat_url_routes_static_then_manual_when_cdp_disabled(self):
        router = AccessStrategyRouter()
        url = (
            "https://mp.weixin.qq.com/s?"
            "__biz=abc&mid=1&idx=1&sn=xyz&scene=21#wechat_redirect"
        )

        strategies = router.route(url, config={"enable_cdp": False})

        self.assertEqual(["static", "manual_required"], strategies)

    def test_wechat_url_routes_static_then_cdp_optional_when_enabled(self):
        router = AccessStrategyRouter()

        strategies = router.route(
            "https://mp.weixin.qq.com/s?__biz=abc&mid=1&idx=1&sn=xyz",
            config={"enable_cdp": True},
        )

        self.assertEqual(["static", "cdp_optional", "manual"], strategies)

    def test_generic_article_routes_jina_then_static(self):
        router = AccessStrategyRouter()

        strategies = router.route("https://example.com/articles/ai-compute")

        self.assertEqual(["jina", "static"], strategies)

    def test_cdp_disabled_does_not_call_cdp_fetcher(self):
        cdp = DummyFetcher("cdp", status="success")
        static = DummyFetcher("static", status="failed")
        layer = WebAccessLayer(
            config={"enable_cdp": False},
            fetchers={"static": static, "cdp_optional": cdp},
        )

        result = layer.fetch("https://mp.weixin.qq.com/s?__biz=abc&mid=1&sn=xyz")

        self.assertEqual("manual_required", result.status)
        self.assertEqual([], cdp.calls)

    def test_wechat_query_parameters_are_not_trimmed(self):
        url = "https://mp.weixin.qq.com/s?__biz=abc&mid=1&idx=1&sn=xyz#wechat_redirect"
        static = DummyFetcher("static", status="success")
        layer = WebAccessLayer(config={"enable_cdp": False}, fetchers={"static": static})

        result = layer.fetch(url)

        self.assertEqual(url, result.url)
        self.assertEqual([url], static.calls)


if __name__ == "__main__":
    unittest.main()
