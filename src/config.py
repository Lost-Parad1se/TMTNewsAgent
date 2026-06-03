"""Configuration loading for TMTNewsAgent."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    """Runtime configuration assembled from YAML files and environment variables."""

    project_root: Path
    sources: Dict[str, Any] = Field(default_factory=dict)
    web_access: Dict[str, Any] = Field(default_factory=dict)
    topics: Dict[str, Any] = Field(default_factory=dict)
    prompts: Dict[str, Any] = Field(default_factory=dict)
    llm_provider: str = "mock"
    llm_base_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: str = "mock-model"
    sqlite_path: Path
    output_dir: Path


def _load_dotenv(path: Path) -> None:
    """Load a small .env file without requiring python-dotenv at runtime."""

    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _read_yaml(path: Path) -> Dict[str, Any]:
    """Read a YAML config file and return an empty dict if it is blank."""

    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def load_config(project_root: Optional[Path] = None) -> AppConfig:
    """Load project configuration from config files and environment variables."""

    root = project_root or Path(__file__).resolve().parents[1]
    _load_dotenv(root / ".env")

    sqlite_env = os.getenv("SQLITE_PATH", "data/processed/tmt_news_agent.db")
    sqlite_path = Path(sqlite_env)
    if not sqlite_path.is_absolute():
        sqlite_path = root / sqlite_path

    output_dir = root / "data" / "outputs"

    return AppConfig(
        project_root=root,
        sources=_read_yaml(root / "config" / "sources.yaml"),
        web_access=_read_yaml(root / "config" / "web_access.yaml").get("web_access", {}),
        topics=_read_yaml(root / "config" / "topics.yaml"),
        prompts=_read_yaml(root / "config" / "prompts.yaml"),
        llm_provider=os.getenv("LLM_PROVIDER", "mock"),
        llm_base_url=os.getenv("LLM_BASE_URL"),
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_model=os.getenv("LLM_MODEL", "mock-model"),
        sqlite_path=sqlite_path,
        output_dir=output_dir,
    )
