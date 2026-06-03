"""Text normalization and lightweight similarity helpers."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher


def clean_whitespace(text: str) -> str:
    """Collapse repeated whitespace while preserving paragraph boundaries."""

    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    non_empty = [line for line in lines if line]
    return "\n".join(non_empty)


def normalize_title(title: str) -> str:
    """Normalize a title for deduplication comparisons."""

    normalized = unicodedata.normalize("NFKC", title or "").lower().strip()
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", "", normalized)
    noise_words = ["原创", "深度", "独家", "重磅", "快讯"]
    for word in noise_words:
        normalized = normalized.replace(word, "")
    return normalized


def truncate_text(text: str, max_chars: int = 4000) -> str:
    """Trim text to a maximum number of characters for prompt construction."""

    if not text or len(text) <= max_chars:
        return text or ""
    return text[: max_chars - 20].rstrip() + "\n...[truncated]"


def simple_similarity(left: str, right: str) -> float:
    """Return a simple 0-1 sequence similarity score."""

    left_norm = normalize_title(left) if len(left) < 200 else clean_whitespace(left)
    right_norm = normalize_title(right) if len(right) < 200 else clean_whitespace(right)
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def stable_article_id(url: str | None, title: str, text: str) -> str:
    """Create a stable short article id from URL, title, and text."""

    import hashlib

    payload = f"{url or ''}|{title}|{text[:500]}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]
