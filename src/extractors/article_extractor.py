"""Public article fetching and metadata extraction."""

from __future__ import annotations

import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

from src.extractors.html_cleaner import HTMLCleaner
from src.models import ArticleRaw
from src.utils.time_utils import now_iso


class ArticleExtractor:
    """Fetch public webpages and extract article metadata and text."""

    def __init__(self, timeout_seconds: int = 15, user_agent: Optional[str] = None):
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent or (
            "TMTNewsAgent/0.1 (+public information research prototype)"
        )
        self.cleaner = HTMLCleaner()

    def fetch_article(self, url: str, source_type: str = "manual_url") -> ArticleRaw:
        """Fetch and parse one public article URL, returning a failure item on errors."""

        try:
            response = requests.get(
                url,
                timeout=self.timeout_seconds,
                headers={"User-Agent": self.user_agent},
            )
            response.raise_for_status()
            response.encoding = response.apparent_encoding or response.encoding
            return self.parse_html(response.text, url=url, source_type=source_type)
        except Exception as exc:  # noqa: BLE001 - errors should not stop the pipeline
            return ArticleRaw(
                source_type=source_type,
                url=url,
                title=url,
                fetched_at=now_iso(),
                fetch_status="failed",
                error_message=str(exc),
                quality_flags=["fetch_failed"],
            )

    def parse_html(
        self, html: str, url: Optional[str] = None, source_type: str = "manual_url"
    ) -> ArticleRaw:
        """Parse HTML into raw article metadata and cleaned text candidates."""

        soup = BeautifulSoup(html or "", "lxml")
        title = self._extract_title(soup) or url or "untitled"
        account_name = self._extract_account_name(soup)
        author = self._extract_author(soup)
        publish_time = self._extract_publish_time(soup, html)
        clean_text, quality_flags = self.cleaner.clean_html(html)

        return ArticleRaw(
            source_type=source_type,
            url=url,
            title=title,
            author=author,
            publish_time=publish_time,
            account_name=account_name,
            raw_html=html,
            raw_text=clean_text,
            fetched_at=now_iso(),
            quality_flags=quality_flags,
        )

    @staticmethod
    def _meta_content(soup: BeautifulSoup, *names: str) -> Optional[str]:
        """Read the first matching meta tag content."""

        for name in names:
            tag = (
                soup.find("meta", attrs={"name": name})
                or soup.find("meta", attrs={"property": name})
                or soup.find("meta", attrs={"itemprop": name})
            )
            if tag and tag.get("content"):
                return tag["content"].strip()
        return None

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract title with WeChat-specific fields first."""

        candidates = [
            soup.find(id="activity-name"),
            soup.find(class_="rich_media_title"),
            soup.find("h1"),
        ]
        for tag in candidates:
            if tag and tag.get_text(strip=True):
                return tag.get_text(" ", strip=True)
        meta_title = self._meta_content(soup, "og:title", "twitter:title")
        if meta_title:
            return meta_title
        if soup.title and soup.title.get_text(strip=True):
            return soup.title.get_text(" ", strip=True)
        return None

    def _extract_account_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract source account or site name."""

        js_name = soup.find(id="js_name")
        if js_name and js_name.get_text(strip=True):
            return js_name.get_text(" ", strip=True)
        return self._meta_content(soup, "author", "og:site_name", "publisher")

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author metadata where available."""

        author = self._meta_content(soup, "author", "article:author")
        if author:
            return author
        author_tag = soup.find(class_=re.compile("author", re.I))
        if author_tag and author_tag.get_text(strip=True):
            return author_tag.get_text(" ", strip=True)
        return None

    def _extract_publish_time(self, soup: BeautifulSoup, html: str) -> Optional[str]:
        """Extract publish time from meta tags or common WeChat script variables."""

        meta_time = self._meta_content(
            soup,
            "article:published_time",
            "publish_time",
            "pubdate",
            "datePublished",
            "og:release_date",
        )
        if meta_time:
            return meta_time

        patterns = [
            r'publish_time\s*[:=]\s*["\']([^"\']+)["\']',
            r'ct\s*=\s*["\']([^"\']+)["\']',
            r'create_time\s*[:=]\s*["\']([^"\']+)["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, html or "")
            if match:
                return match.group(1).strip()
        return None
