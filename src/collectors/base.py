"""Base collector interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from src.models import ArticleRaw


class BaseCollector(ABC):
    """Abstract collector that returns raw article candidates."""

    @abstractmethod
    def collect(self) -> List[ArticleRaw]:
        """Collect article candidates from one source."""
