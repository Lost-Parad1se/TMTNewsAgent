"""Core contracts for compliant web access fetchers."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from src.utils.time_utils import now_iso


class FetchResult(BaseModel):
    """Normalized result returned by one web access strategy."""

    url: str
    final_url: Optional[str] = None
    strategy: str
    status: str
    title: Optional[str] = None
    html: Optional[str] = None
    markdown: Optional[str] = None
    text: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    fetched_at: str = Field(default_factory=now_iso)


class BaseFetcher:
    """Base class for one URL fetching strategy."""

    strategy_name = "base"

    def fetch(self, url: str) -> FetchResult:
        """Fetch one URL and return a normalized, non-throwing result."""

        raise NotImplementedError
