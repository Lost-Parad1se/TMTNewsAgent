"""Command line entry point for TMTNewsAgent."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from src.config import load_config
from src.llm.provider_registry import supported_provider_names
from src.main import NewsResearchAgent


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(description="Run the TMT news research agent.")
    parser.add_argument(
        "--mode",
        choices=["csv", "manual_url", "search", "browser_history"],
        required=True,
    )
    parser.add_argument("--topic", required=True, help="Research topic for the final brief.")
    parser.add_argument("--keywords", nargs="*", default=[], help="Search keywords.")
    parser.add_argument("--urls", nargs="*", default=[], help="Public article URLs.")
    parser.add_argument("--csv-path", default=None, help="Path to CSV article data.")
    parser.add_argument("--date", default=None, help="Brief date, YYYY-MM-DD.")
    parser.add_argument(
        "--llm-provider",
        choices=supported_provider_names(),
        default=None,
        help="LLM provider override for this run.",
    )
    parser.add_argument(
        "--llm-model",
        default=None,
        help="LLM model override for this run.",
    )
    parser.add_argument(
        "--web-access-strategy",
        choices=["auto", "static", "jina", "cdp", "manual"],
        default="auto",
        help="Web access strategy for URL-based collection.",
    )
    parser.add_argument(
        "--enable-cdp",
        action="store_true",
        help="Allow optional local-browser CDP reading through localhost:3456.",
    )
    parser.add_argument(
        "--enable-browser-history",
        action="store_true",
        help="Enable explicit local browser history lookup.",
    )
    parser.add_argument(
        "--browser",
        choices=["chrome", "edge", "all"],
        default="all",
        help="Browser history source.",
    )
    parser.add_argument("--since", default="7d", help="Browser history time window.")
    parser.add_argument(
        "--max-browser-history-results",
        type=int,
        default=20,
        help="Maximum matched browser history entries.",
    )
    return parser


def main(argv: List[str] | None = None) -> None:
    """Parse arguments, run the agent, and print output paths."""

    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(Path(__file__).resolve().parents[1])
    if args.llm_provider:
        config.llm_provider = args.llm_provider
    if args.llm_model:
        config.llm_model = args.llm_model
    agent = NewsResearchAgent(config)
    result = agent.run(
        mode=args.mode,
        topic=args.topic,
        keywords=args.keywords,
        urls=args.urls,
        csv_path=args.csv_path,
        date=args.date,
        web_access_strategy=args.web_access_strategy,
        enable_cdp=args.enable_cdp,
        enable_browser_history=args.enable_browser_history,
        browser=args.browser,
        since=args.since,
        max_browser_history_results=args.max_browser_history_results,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
