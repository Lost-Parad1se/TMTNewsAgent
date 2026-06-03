"""Optional, compliant web access layer for public article collection."""

from src.web_access.base import BaseFetcher, FetchResult
from src.web_access.strategy_router import AccessStrategyRouter, WebAccessLayer

__all__ = [
    "AccessStrategyRouter",
    "BaseFetcher",
    "FetchResult",
    "WebAccessLayer",
]
