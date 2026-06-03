"""Logging helpers for the agent workflow."""

from __future__ import annotations

import logging
from typing import Optional


def get_logger(name: str = "tmt_news_agent", level: int = logging.INFO) -> logging.Logger:
    """Return a configured logger with a consistent console format."""

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def configure_logger(level_name: Optional[str] = None) -> logging.Logger:
    """Configure and return the root project logger."""

    level = getattr(logging, (level_name or "INFO").upper(), logging.INFO)
    return get_logger(level=level)
