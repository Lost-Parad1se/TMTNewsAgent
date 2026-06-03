"""Optional local browser history collector with privacy-preserving filtering."""

from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Sequence

from src.collectors.base import BaseCollector
from src.models import ArticleRaw
from src.utils.logger import get_logger
from src.utils.time_utils import now_iso


CHROMIUM_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)


@dataclass
class BrowserHistoryMatch:
    """Minimal, filtered browser history match."""

    url: str
    title: str
    last_visit_time: str
    browser: str


class BrowserHistoryCollector(BaseCollector):
    """Read matching local browser history entries only when explicitly enabled."""

    def __init__(
        self,
        keywords: Iterable[str],
        since: str = "7d",
        browser: str = "all",
        limit: int = 20,
        enabled: bool = False,
    ):
        self.keywords = [keyword.lower() for keyword in keywords if keyword]
        self.since = since
        self.browser = browser
        self.limit = limit
        self.enabled = enabled
        self.logger = get_logger(__name__)

    def collect(self) -> List[ArticleRaw]:
        """Return ArticleRaw shells for matching history entries."""

        articles: List[ArticleRaw] = []
        for match in self.collect_matches():
            articles.append(
                ArticleRaw(
                    source_type="browser_history",
                    url=match.url,
                    title=match.title or match.url,
                    raw_text=(
                        "本地浏览器历史匹配项；正文读取可通过 WebAccessLayer 或 CSV/手动正文补充。"
                    ),
                    fetched_at=now_iso(),
                    fetch_status="success",
                    fetch_strategy="browser_history",
                    fetch_metadata={
                        "strategy": "browser_history",
                        "last_visit_time": match.last_visit_time,
                        "browser": match.browser,
                    },
                    quality_flags=["browser_history_match"],
                )
            )
        return articles

    def collect_urls(self) -> List[str]:
        """Return only matching URLs for downstream article fetching."""

        return [match.url for match in self.collect_matches()]

    def collect_matches(self) -> List[BrowserHistoryMatch]:
        """Read browser history and keep only keyword-matched rows."""

        if not self.enabled:
            self.logger.info("Browser history collection is disabled.")
            return []
        if not self.keywords:
            self.logger.warning("Browser history mode requires at least one keyword.")
            return []

        matches: List[BrowserHistoryMatch] = []
        for browser_name, history_path in self._candidate_history_paths():
            if len(matches) >= self.limit:
                break
            if not history_path.exists():
                continue
            matches.extend(self._read_history_file(browser_name, history_path))
        return matches[: self.limit]

    def _read_history_file(
        self, browser_name: str, history_path: Path
    ) -> List[BrowserHistoryMatch]:
        since_cutoff = self._since_cutoff()
        since_chromium = int((since_cutoff - CHROMIUM_EPOCH).total_seconds() * 1_000_000)
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(prefix="tmt_history_", delete=False) as tmp_file:
                tmp_path = Path(tmp_file.name)
            shutil.copy2(history_path, tmp_path)
            clauses = []
            params: List[object] = [since_chromium]
            for keyword in self.keywords:
                clauses.append("(lower(urls.url) LIKE ? OR lower(urls.title) LIKE ?)")
                like = f"%{keyword}%"
                params.extend([like, like])
            params.append(self.limit)
            query = (
                "SELECT urls.url, urls.title, urls.last_visit_time "
                "FROM urls "
                "WHERE urls.last_visit_time >= ? AND ("
                + " OR ".join(clauses)
                + ") ORDER BY urls.last_visit_time DESC LIMIT ?"
            )
            rows: List[BrowserHistoryMatch] = []
            with sqlite3.connect(tmp_path) as conn:
                for url, title, last_visit_time in conn.execute(query, params):
                    rows.append(
                        BrowserHistoryMatch(
                            url=url,
                            title=title or url,
                            last_visit_time=self._format_chromium_time(last_visit_time),
                            browser=browser_name,
                        )
                    )
            return rows
        except Exception as exc:  # noqa: BLE001 - optional adapter fallback
            self.logger.warning("Failed to read %s history: %s", browser_name, exc)
            return []
        finally:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def _candidate_history_paths(self) -> Sequence[tuple[str, Path]]:
        home = Path.home()
        browser = self.browser.lower()
        candidates: List[tuple[str, Path]] = []

        if os.name == "nt":
            local_appdata = Path(os.getenv("LOCALAPPDATA", ""))
            if browser in {"all", "edge"}:
                candidates.append(
                    (
                        "edge",
                        local_appdata
                        / "Microsoft"
                        / "Edge"
                        / "User Data"
                        / "Default"
                        / "History",
                    )
                )
            if browser in {"all", "chrome"}:
                candidates.append(
                    (
                        "chrome",
                        local_appdata
                        / "Google"
                        / "Chrome"
                        / "User Data"
                        / "Default"
                        / "History",
                    )
                )
            return candidates

        if browser in {"all", "edge"}:
            candidates.append(
                (
                    "edge",
                    home
                    / "Library"
                    / "Application Support"
                    / "Microsoft Edge"
                    / "Default"
                    / "History",
                )
            )
        if browser in {"all", "chrome"}:
            candidates.append(
                (
                    "chrome",
                    home
                    / "Library"
                    / "Application Support"
                    / "Google"
                    / "Chrome"
                    / "Default"
                    / "History",
                )
            )
        return candidates

    def _since_cutoff(self) -> datetime:
        value = (self.since or "7d").strip().lower()
        try:
            days = int(value[:-1]) if value.endswith("d") else int(value)
        except ValueError:
            days = 7
        return datetime.now(timezone.utc) - timedelta(days=days)

    @staticmethod
    def _format_chromium_time(value: int) -> str:
        return (CHROMIUM_EPOCH + timedelta(microseconds=int(value))).isoformat()
