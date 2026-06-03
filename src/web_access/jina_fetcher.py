"""Jina Reader fetcher for article-to-markdown extraction."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from src.web_access.base import BaseFetcher, FetchResult
from src.web_access.validators import extract_title_from_markdown


DEFAULT_JINA_BASE_URL = "https://r.jina.ai/"


def normalize_jina_url(url: str, base_url: str = DEFAULT_JINA_BASE_URL) -> str:
    """Return the Jina Reader URL without duplicating the reader prefix."""

    reader_prefix = base_url.rstrip("/") + "/"
    if (url or "").startswith(reader_prefix):
        return url
    return f"{reader_prefix}{url}"


class JinaFetcher(BaseFetcher):
    """Fetch article content via Jina Reader's public reader endpoint."""

    strategy_name = "jina"

    def __init__(
        self,
        timeout_seconds: int = 20,
        base_url: str = DEFAULT_JINA_BASE_URL,
        user_agent: Optional[str] = None,
    ):
        self.timeout_seconds = timeout_seconds
        self.base_url = base_url
        self.user_agent = user_agent or (
            "TMTNewsAgent/0.1 (+public information research prototype)"
        )

    def fetch(self, url: str) -> FetchResult:
        """Fetch markdown through Jina Reader, returning failed on extraction errors."""

        jina_url = normalize_jina_url(url, self.base_url)
        metadata: Dict[str, Any] = {
            "jina_url": jina_url,
            "extraction_loss_risk": True,
        }
        try:
            response = requests.get(
                jina_url,
                timeout=self.timeout_seconds,
                headers={"User-Agent": self.user_agent},
            )
            metadata["http_status"] = response.status_code
            if response.status_code < 200 or response.status_code >= 300:
                return FetchResult(
                    url=url,
                    final_url=response.url,
                    strategy=self.strategy_name,
                    status="failed",
                    error=f"Jina Reader HTTP {response.status_code}",
                    metadata=metadata,
                )

            markdown = response.text or ""
            if not markdown.strip():
                return FetchResult(
                    url=url,
                    final_url=response.url,
                    strategy=self.strategy_name,
                    status="failed",
                    error="Jina Reader returned empty content",
                    metadata=metadata,
                )

            return FetchResult(
                url=url,
                final_url=response.url,
                strategy=self.strategy_name,
                status="success",
                title=extract_title_from_markdown(markdown),
                markdown=markdown,
                text=markdown,
                metadata=metadata,
            )
        except Exception as exc:  # noqa: BLE001 - item-level fetch fallback
            return FetchResult(
                url=url,
                strategy=self.strategy_name,
                status="failed",
                error=str(exc),
                metadata=metadata,
            )
