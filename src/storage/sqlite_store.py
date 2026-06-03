"""SQLite persistence for articles, summaries, and briefs."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict

from pydantic import BaseModel

from src.models import ArticleProcessed, ArticleRaw, ResearchBrief, model_to_dict


class SQLiteStore:
    """Persist article metadata and generated outputs in SQLite."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def init_db(self) -> None:
        """Create tables if they do not already exist."""

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS raw_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    title TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_articles (
                    article_id TEXT PRIMARY KEY,
                    url TEXT,
                    title TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS research_briefs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def save_raw_article(self, article: ArticleRaw) -> None:
        """Persist one raw article."""

        payload = self._json(article)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO raw_articles (url, title, source_type, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (article.url, article.title, article.source_type, payload),
            )

    def save_processed_article(self, article: ArticleProcessed) -> None:
        """Persist or replace one processed article."""

        payload = self._json(article)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO processed_articles
                (article_id, url, title, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (article.article_id, article.url, article.title, payload),
            )

    def save_brief(self, brief: ResearchBrief) -> None:
        """Persist one research brief."""

        payload = self._json(brief)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO research_briefs (date, topic, payload_json)
                VALUES (?, ?, ?)
                """,
                (brief.date, brief.topic, payload),
            )

    @staticmethod
    def _json(model: BaseModel | Dict[str, Any]) -> str:
        """Serialize a model or dict to JSON."""

        payload = model_to_dict(model) if isinstance(model, BaseModel) else model
        return json.dumps(payload, ensure_ascii=False)
