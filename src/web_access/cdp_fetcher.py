"""Optional local-browser CDP fetcher through a user-run proxy."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from src.web_access.base import BaseFetcher, FetchResult
from src.web_access.validators import has_access_limit_text


class CDPFetcher(BaseFetcher):
    """Read a small number of URLs via a local CDP proxy when explicitly enabled."""

    strategy_name = "cdp"

    def __init__(
        self,
        enable_cdp: bool = False,
        proxy_url: str = "http://localhost:3456",
        timeout_seconds: int = 15,
    ):
        self.enable_cdp = enable_cdp
        self.proxy_url = proxy_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def fetch(self, url: str) -> FetchResult:
        """Fetch one URL through the local proxy without touching existing tabs."""

        if not self.enable_cdp:
            return self._manual_required(
                url,
                "CDP is disabled. Pass --enable-cdp to allow local browser assistance.",
            )

        tab_id: Optional[str] = None
        try:
            if not self._is_proxy_healthy():
                return self._manual_required(
                    url,
                    "Local CDP proxy is unavailable at http://localhost:3456. "
                    "Enable the local browser helper, or use manual paste/CSV mode.",
                )

            open_payload = self._post_new(url)
            tab_id = self._extract_tab_id(open_payload)
            if not tab_id:
                return self._manual_required(
                    url,
                    "CDP proxy did not return a created tab id.",
                    metadata={"proxy_response": open_payload},
                )

            expression = (
                "(() => ({"
                "title: document.title || '',"
                "text: document.body ? document.body.innerText : '',"
                "html: document.documentElement ? document.documentElement.outerHTML : ''"
                "}))()"
            )
            result = self._post_eval(tab_id, expression)
            payload = self._extract_eval_payload(result)
            title = str(payload.get("title") or "").strip() or None
            text = str(payload.get("text") or "").strip()
            html = str(payload.get("html") or "").strip() or None
            status = "partial" if has_access_limit_text(text) else "success"
            error = (
                "Browser text suggests the page may require a different access method "
                "or user permission; do not assume the article is nonexistent."
                if status == "partial"
                else None
            )
            return FetchResult(
                url=url,
                strategy=self.strategy_name,
                status=status,
                title=title,
                html=html,
                text=text,
                error=error,
                metadata={"cdp_used": True, "tab_id": tab_id},
            )
        except Exception as exc:  # noqa: BLE001 - item-level fetch fallback
            return self._manual_required(
                url,
                f"CDP fetch failed: {exc}",
                metadata={"cdp_used": False},
            )
        finally:
            if tab_id:
                self._close_tab(tab_id)

    def _is_proxy_healthy(self) -> bool:
        response = requests.get(f"{self.proxy_url}/health", timeout=3)
        return 200 <= response.status_code < 300

    def _post_new(self, url: str) -> Dict[str, Any]:
        response = requests.post(
            f"{self.proxy_url}/new",
            data=url,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return self._response_payload(response)

    def _post_eval(self, tab_id: str, expression: str) -> Dict[str, Any]:
        response = requests.post(
            f"{self.proxy_url}/eval",
            params={"target": tab_id, "tab_id": tab_id, "id": tab_id},
            data=expression,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return self._response_payload(response)

    def _close_tab(self, tab_id: str) -> None:
        try:
            requests.get(
                f"{self.proxy_url}/close",
                params={"target": tab_id, "tab_id": tab_id, "id": tab_id},
                timeout=5,
            )
        except Exception:
            return

    @staticmethod
    def _response_payload(response: requests.Response) -> Dict[str, Any]:
        try:
            data = response.json()
        except ValueError:
            data = response.text
        return data if isinstance(data, dict) else {"result": data}

    @staticmethod
    def _extract_tab_id(payload: Dict[str, Any]) -> Optional[str]:
        for key in ("tab_id", "id", "targetId", "target_id"):
            if payload.get(key):
                return str(payload[key])
        nested = payload.get("result")
        if isinstance(nested, dict):
            return CDPFetcher._extract_tab_id(nested)
        return None

    @staticmethod
    def _extract_eval_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        result = payload.get("result", payload)
        if isinstance(result, dict) and "value" in result and isinstance(result["value"], dict):
            return result["value"]
        if isinstance(result, dict):
            return result
        return {"text": str(result or "")}

    def _manual_required(
        self,
        url: str,
        error: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FetchResult:
        return FetchResult(
            url=url,
            strategy=self.strategy_name,
            status="manual_required",
            title=url,
            error=error,
            metadata=metadata or {"cdp_used": False},
        )
