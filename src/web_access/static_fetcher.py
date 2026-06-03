"""Static HTTP fetcher for public article pages."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from src.web_access.base import BaseFetcher, FetchResult
from src.web_access.validators import (
    extract_text_from_html,
    extract_title_from_html,
    has_access_limit_text,
)


class StaticFetcher(BaseFetcher):
    """Fetch public pages with a single static HTTP request."""

    strategy_name = "static"

    def __init__(
        self,
        timeout_seconds: int = 15,
        user_agent: Optional[str] = None,
    ):
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent or (
            "TMTNewsAgent/0.1 (+public information research prototype)"
        )

    def fetch(self, url: str) -> FetchResult:
        """Fetch one URL without high-frequency retries or pipeline-breaking errors."""

        try:
            response = requests.get(
                url,
                timeout=self.timeout_seconds,
                headers={"User-Agent": self.user_agent},
            )
            metadata: Dict[str, Any] = {
                "http_status": response.status_code,
                "content_type": response.headers.get("Content-Type"),
            }
            if response.status_code < 200 or response.status_code >= 300:
                return FetchResult(
                    url=url,
                    final_url=response.url,
                    strategy=self.strategy_name,
                    status="failed",
                    error=f"HTTP {response.status_code}",
                    metadata=metadata,
                )

            response.encoding = response.apparent_encoding or response.encoding
            html = response.text or ""
            text = extract_text_from_html(html)
            title = extract_title_from_html(html)
            status = "partial" if has_access_limit_text(text) else "success"
            error = (
                "Page text suggests an access or permission limitation; "
                "static fetch result may be incomplete."
                if status == "partial"
                else None
            )
            return FetchResult(
                url=url,
                final_url=response.url,
                strategy=self.strategy_name,
                status=status,
                title=title,
                html=html,
                text=text,
                error=error,
                metadata=metadata,
            )
        except Exception as exc:  # noqa: BLE001 - item-level fetch fallback
            return FetchResult(
                url=url,
                strategy=self.strategy_name,
                status="failed",
                error=str(exc),
                metadata={"timeout_seconds": self.timeout_seconds},
            )
