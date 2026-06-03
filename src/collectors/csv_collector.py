"""CSV collector for manually curated article rows."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from src.collectors.base import BaseCollector
from src.models import ArticleRaw
from src.utils.logger import get_logger
from src.utils.time_utils import now_iso


class CSVCollector(BaseCollector):
    """Read article metadata and text from a local CSV file."""

    def __init__(self, csv_path: str | Path):
        self.csv_path = Path(csv_path)
        self.logger = get_logger(__name__)

    def collect(self) -> List[ArticleRaw]:
        """Load articles from CSV columns: title, url, account_name, publish_time, raw_text."""

        if not self.csv_path.exists():
            self.logger.warning("CSV file does not exist: %s", self.csv_path)
            return []

        articles: List[ArticleRaw] = []
        with self.csv_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            for index, row in enumerate(reader, start=1):
                title = (row.get("title") or "").strip()
                raw_text = (row.get("raw_text") or "").strip()
                if not title and not raw_text:
                    self.logger.warning("Skipping empty CSV row %s", index)
                    continue
                articles.append(
                    ArticleRaw(
                        source_type="csv",
                        url=(row.get("url") or "").strip() or None,
                        title=title or f"csv-row-{index}",
                        account_name=(row.get("account_name") or "").strip() or None,
                        publish_time=(row.get("publish_time") or "").strip() or None,
                        raw_text=raw_text,
                        fetched_at=now_iso(),
                    )
                )
        self.logger.info("Loaded %s articles from CSV", len(articles))
        return articles
