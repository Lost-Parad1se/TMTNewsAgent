"""HTML cleaning utilities for article text extraction."""

from __future__ import annotations

from typing import List, Tuple

from bs4 import BeautifulSoup

from src.utils.text_utils import clean_whitespace


class HTMLCleaner:
    """Clean HTML and extract readable article text."""

    def clean_html(self, html: str) -> Tuple[str, List[str]]:
        """Return cleaned text and quality flags for an HTML document."""

        if not html:
            return "", ["empty_html", "low_quality"]

        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
            tag.decompose()

        main = (
            soup.find(id="js_content")
            or soup.find("article")
            or soup.find("main")
            or soup.find("body")
            or soup
        )
        text = clean_whitespace(main.get_text("\n", strip=True))

        flags: List[str] = []
        if len(text) < 200:
            flags.append("low_quality")
        return text, flags

    def clean_text(self, text: str) -> Tuple[str, List[str]]:
        """Normalize plain text and apply lightweight quality checks."""

        clean_text = clean_whitespace(text)
        flags: List[str] = []
        if not clean_text:
            flags.append("empty_text")
        if len(clean_text) < 200:
            flags.append("low_quality")
        return clean_text, flags
