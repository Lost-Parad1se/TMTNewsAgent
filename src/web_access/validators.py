"""URL and content validators for the Web Access Layer."""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from src.utils.text_utils import clean_whitespace


WECHAT_HOSTS = {"mp.weixin.qq.com"}
ACCESS_LIMIT_PATTERNS = (
    "内容不存在",
    "访问受限",
    "请在微信客户端打开",
    "验证码",
    "登录",
    "permission",
    "forbidden",
)


def is_wechat_url(url: str) -> bool:
    """Return True when the URL is a WeChat public account article URL."""

    parsed = urlparse(url or "")
    return parsed.netloc.lower() in WECHAT_HOSTS


def is_pdf_url(url: str) -> bool:
    """Return True when the URL path looks like a PDF resource."""

    parsed = urlparse(url or "")
    return parsed.path.lower().endswith(".pdf")


def is_probably_url(value: str) -> bool:
    """Lightweight URL check used by router and collectors."""

    parsed = urlparse(value or "")
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def extract_title_from_html(html: str) -> Optional[str]:
    """Extract a readable title from common article HTML fields."""

    soup = BeautifulSoup(html or "", "lxml")
    candidates = [
        soup.find(id="activity-name"),
        soup.find(class_="rich_media_title"),
        soup.find("h1"),
    ]
    for tag in candidates:
        if tag and tag.get_text(strip=True):
            return tag.get_text(" ", strip=True)

    for name in ("og:title", "twitter:title"):
        tag = soup.find("meta", attrs={"property": name}) or soup.find(
            "meta", attrs={"name": name}
        )
        if tag and tag.get("content"):
            return tag["content"].strip()

    if soup.title and soup.title.get_text(strip=True):
        return soup.title.get_text(" ", strip=True)
    return None


def extract_text_from_html(html: str) -> str:
    """Extract best-effort readable text from article HTML."""

    soup = BeautifulSoup(html or "", "lxml")
    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()
    main = (
        soup.find(id="js_content")
        or soup.find("article")
        or soup.find("main")
        or soup.find("body")
        or soup
    )
    return clean_whitespace(main.get_text("\n", strip=True))


def extract_title_from_markdown(markdown: str) -> Optional[str]:
    """Extract title from the first markdown heading when available."""

    for line in (markdown or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return re.sub(r"^#+\s*", "", stripped).strip() or None
        if stripped:
            return stripped[:120]
    return None


def has_access_limit_text(text: str) -> bool:
    """Detect common access-limit wording without assuming the article is gone."""

    lowered = (text or "").lower()
    return any(pattern.lower() in lowered for pattern in ACCESS_LIMIT_PATTERNS)
