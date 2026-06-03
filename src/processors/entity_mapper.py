"""Company entity mapping using configurable alias dictionaries."""

from __future__ import annotations

from typing import Dict, Iterable, List


class EntityMapper:
    """Identify known TMT companies from titles and article text."""

    def __init__(self, company_aliases: Dict[str, Iterable[str]] | None = None):
        self.company_aliases = company_aliases or {}

    def map_companies(self, title: str, text: str) -> List[str]:
        """Return company tags whose aliases occur in the article."""

        haystack = f"{title}\n{text}".lower()
        matched: List[str] = []
        for company, aliases in self.company_aliases.items():
            for alias in aliases:
                if alias and alias.lower() in haystack:
                    matched.append(company)
                    break
        return matched
