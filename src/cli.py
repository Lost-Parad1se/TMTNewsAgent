"""Command line entry point for TMTNewsAgent."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from src.config import load_config
from src.main import NewsResearchAgent


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(description="Run the TMT news research agent.")
    parser.add_argument("--mode", choices=["csv", "manual_url", "search"], required=True)
    parser.add_argument("--topic", required=True, help="Research topic for the final brief.")
    parser.add_argument("--keywords", nargs="*", default=[], help="Search keywords.")
    parser.add_argument("--urls", nargs="*", default=[], help="Public article URLs.")
    parser.add_argument("--csv-path", default=None, help="Path to CSV article data.")
    parser.add_argument("--date", default=None, help="Brief date, YYYY-MM-DD.")
    return parser


def main(argv: List[str] | None = None) -> None:
    """Parse arguments, run the agent, and print output paths."""

    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(Path(__file__).resolve().parents[1])
    agent = NewsResearchAgent(config)
    result = agent.run(
        mode=args.mode,
        topic=args.topic,
        keywords=args.keywords,
        urls=args.urls,
        csv_path=args.csv_path,
        date=args.date,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
