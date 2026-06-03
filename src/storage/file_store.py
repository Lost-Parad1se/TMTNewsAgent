"""Filesystem output helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict


class FileStore:
    """Save JSON and Markdown outputs under data/outputs."""

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_json(self, filename: str, payload: Dict[str, Any]) -> Path:
        """Save a JSON file with UTF-8 encoding."""

        path = self.output_dir / filename
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def save_markdown(self, filename: str, content: str) -> Path:
        """Save a Markdown file with UTF-8 encoding."""

        path = self.output_dir / filename
        path.write_text(content, encoding="utf-8")
        return path


def slugify(value: str, max_length: int = 50) -> str:
    """Create a filesystem-friendly slug while preserving Chinese characters."""

    value = re.sub(r"[^\w\u4e00-\u9fff]+", "_", value.strip(), flags=re.U)
    value = re.sub(r"_+", "_", value).strip("_")
    return (value or "brief")[:max_length]
