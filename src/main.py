"""Agent workflow orchestration for TMT news research briefs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from src.collectors.csv_collector import CSVCollector
from src.collectors.manual_url_collector import ManualURLCollector
from src.collectors.search_collector import SearchCollector
from src.config import AppConfig, load_config
from src.extractors.html_cleaner import HTMLCleaner
from src.llm.factory import build_llm_client
from src.models import ArticleProcessed, ArticleRaw, PipelineReport, model_to_dict
from src.processors.classifier import build_classifier_from_config
from src.processors.deduplicator import Deduplicator
from src.processors.entity_mapper import EntityMapper
from src.processors.report_writer import ReportWriter
from src.processors.summarizer import ArticleSummarizer
from src.storage.file_store import FileStore, slugify
from src.storage.sqlite_store import SQLiteStore
from src.utils.logger import get_logger
from src.utils.text_utils import clean_whitespace, stable_article_id
from src.utils.time_utils import today_str
from src.web_access.browser_history_collector import BrowserHistoryCollector
from src.web_access.strategy_router import WebAccessLayer


class NewsResearchAgent:
    """End-to-end agentic workflow for collecting and briefing TMT news."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or load_config()
        self.logger = get_logger(__name__)
        self.cleaner = HTMLCleaner()
        self.entity_mapper = EntityMapper(
            self.config.topics.get("company_aliases", {})
        )
        self.classifier = build_classifier_from_config(self.config.topics)
        self.deduplicator = Deduplicator()
        self.report_writer = ReportWriter()
        self.file_store = FileStore(self.config.output_dir)
        self.sqlite_store = SQLiteStore(self.config.sqlite_path)
        self.web_access_layer = WebAccessLayer(self.config.web_access)
        self.summarizer = ArticleSummarizer(
            llm_client=self._build_llm_client(),
            prompt_template=self.config.prompts.get("single_article_summary", "{text}"),
        )

    def run(
        self,
        mode: str,
        topic: str,
        keywords: Optional[Iterable[str]] = None,
        urls: Optional[Iterable[str]] = None,
        csv_path: Optional[str | Path] = None,
        date: Optional[str] = None,
        web_access_strategy: Optional[str] = None,
        enable_cdp: bool = False,
        enable_browser_history: bool = False,
        browser: str = "all",
        since: str = "7d",
        max_browser_history_results: int = 20,
        search_site_filter: Optional[str] = None,
        search_recent_days: int = 7,
        max_search_results: int = 5,
    ) -> Dict[str, Any]:
        """Run the complete collect-process-summarize-report pipeline."""

        self._apply_web_access_runtime_options(
            strategy=web_access_strategy,
            enable_cdp=enable_cdp,
            enable_browser_history=enable_browser_history,
            browser=browser,
            since=since,
            max_browser_history_results=max_browser_history_results,
        )
        run_date = date or today_str()
        report = PipelineReport()
        self.logger.info("Starting pipeline mode=%s topic=%s date=%s", mode, topic, run_date)

        raw_articles = self._collect(
            mode,
            keywords=keywords,
            urls=urls,
            csv_path=csv_path,
            browser=browser,
            since=since,
            enable_browser_history=enable_browser_history,
            max_browser_history_results=max_browser_history_results,
            search_site_filter=search_site_filter,
            search_recent_days=search_recent_days,
            max_search_results=max_search_results,
        )
        report.collected_count = len(raw_articles)
        self._apply_fetch_report(raw_articles, report)
        for article in raw_articles:
            self.sqlite_store.save_raw_article(article)

        cleaned_articles = self._extract_and_clean(raw_articles, report)
        report.extracted_count = len(cleaned_articles)

        deduped = self.deduplicator.deduplicate(cleaned_articles)
        unique_articles = deduped.unique_articles
        report.deduplicated_count = len(unique_articles)
        self.logger.info("Deduplicated %s -> %s", len(cleaned_articles), len(unique_articles))

        processed_articles = self._process_articles(unique_articles, report)
        report.summarized_count = len(processed_articles)

        brief = self.report_writer.build_brief(processed_articles, topic=topic, date=run_date)
        markdown = self.report_writer.to_markdown(brief)
        filename_base = f"{run_date}_{slugify(topic)}"

        brief_markdown_path = self.file_store.save_markdown(
            f"brief_{filename_base}.md", markdown
        )
        brief_json_path = self.file_store.save_json(
            f"brief_{filename_base}.json", model_to_dict(brief)
        )
        pipeline_report_path = self.file_store.save_json(
            "pipeline_report.json",
            {
                **model_to_dict(report),
                "dedup_report": deduped.dedup_report,
                "duplicate_groups": deduped.duplicate_groups,
            },
        )

        self.sqlite_store.save_brief(brief)
        report.output_files = {
            "brief_markdown_path": str(brief_markdown_path),
            "brief_json_path": str(brief_json_path),
            "pipeline_report_path": str(pipeline_report_path),
            "sqlite_path": str(self.config.sqlite_path),
        }
        self.file_store.save_json(
            "pipeline_report.json",
            {
                **model_to_dict(report),
                "dedup_report": deduped.dedup_report,
                "duplicate_groups": deduped.duplicate_groups,
            },
        )

        self.logger.info("Pipeline finished. Markdown: %s", brief_markdown_path)
        return {
            "status": "success",
            "brief_markdown_path": str(brief_markdown_path),
            "brief_json_path": str(brief_json_path),
            "pipeline_report": model_to_dict(report),
        }

    def _collect(
        self,
        mode: str,
        keywords: Optional[Iterable[str]],
        urls: Optional[Iterable[str]],
        csv_path: Optional[str | Path],
        browser: str = "all",
        since: str = "7d",
        enable_browser_history: bool = False,
        max_browser_history_results: int = 20,
        search_site_filter: Optional[str] = None,
        search_recent_days: int = 7,
        max_search_results: int = 5,
    ) -> List[ArticleRaw]:
        """Collect raw articles according to the selected input mode."""

        self.logger.info("Step 1/8: collecting articles")
        if mode == "csv":
            path = csv_path or self.config.sources.get("csv", {}).get(
                "default_path", "data/raw/articles.csv"
            )
            path = Path(path)
            if not path.is_absolute():
                path = self.config.project_root / path
            return CSVCollector(path).collect()
        if mode == "manual_url":
            max_urls = self.config.sources.get("request_policy", {}).get("max_urls_per_run", 20)
            max_urls = int(self.config.web_access.get("max_urls_per_run", max_urls))
            return ManualURLCollector(
                urls or [],
                web_access_layer=self.web_access_layer,
                max_urls=max_urls,
            ).collect()
        if mode == "search":
            provider = self.config.sources.get("search", {}).get("provider", "mock")
            return SearchCollector(
                keywords or [],
                provider=provider,
                web_access_layer=self.web_access_layer,
                site_filter=search_site_filter,
                recent_days=search_recent_days,
                max_results=max_search_results,
            ).collect()
        if mode == "browser_history":
            return BrowserHistoryCollector(
                keywords=keywords or [],
                since=since,
                browser=browser,
                limit=max_browser_history_results,
                enabled=enable_browser_history,
            ).collect()
        raise ValueError(f"Unsupported mode: {mode}")

    def _apply_web_access_runtime_options(
        self,
        strategy: Optional[str],
        enable_cdp: bool,
        enable_browser_history: bool,
        browser: str,
        since: str,
        max_browser_history_results: int,
    ) -> None:
        """Merge CLI/API runtime flags into the optional web access config."""

        if strategy:
            self.config.web_access["strategy"] = strategy
        if enable_cdp:
            self.config.web_access["enable_cdp"] = True
        if enable_browser_history:
            self.config.web_access["enable_browser_history"] = True
        self.config.web_access["browser"] = browser
        self.config.web_access["since"] = since
        self.config.web_access["max_browser_history_results"] = max_browser_history_results
        self.web_access_layer = WebAccessLayer(self.config.web_access)

    def _apply_fetch_report(self, raw_articles: List[ArticleRaw], report: PipelineReport) -> None:
        """Populate fetch strategy counters and fetch failure details."""

        summary = WebAccessLayer.summarize_results(raw_articles)
        report.fetch_strategy_stats = summary["fetch_strategy_stats"]
        report.cdp_used_count = summary["cdp_used_count"]
        report.manual_required_count = summary["manual_required_count"]
        report.failed_fetch_items = summary["failed_fetch_items"]

    def _extract_and_clean(
        self, raw_articles: List[ArticleRaw], report: PipelineReport
    ) -> List[ArticleRaw]:
        """Clean article text and retain per-item failures."""

        self.logger.info("Step 2/8: extracting and cleaning text")
        cleaned: List[ArticleRaw] = []
        for article in raw_articles:
            try:
                if article.fetch_status not in {"success", "partial"}:
                    report.failed_items.append(
                        {
                            "title": article.title,
                            "url": article.url,
                            "stage": "collect",
                            "error": article.error_message,
                        }
                    )
                    continue

                text = article.raw_text or ""
                flags = list(article.quality_flags)
                if article.raw_html and not text:
                    text, flags = self.cleaner.clean_html(article.raw_html)
                else:
                    text, text_flags = self.cleaner.clean_text(text)
                    flags.extend(flag for flag in text_flags if flag not in flags)

                if not text:
                    report.failed_items.append(
                        {
                            "title": article.title,
                            "url": article.url,
                            "stage": "clean",
                            "error": "empty text",
                        }
                    )
                    continue
                article.raw_text = clean_whitespace(text)
                article.quality_flags = flags
                cleaned.append(article)
            except Exception as exc:  # noqa: BLE001 - item-level fallback
                report.failed_items.append(
                    {
                        "title": article.title,
                        "url": article.url,
                        "stage": "clean",
                        "error": str(exc),
                    }
                )
                self.logger.warning("Failed to clean article %s: %s", article.title, exc)
        return cleaned

    def _process_articles(
        self, articles: List[ArticleRaw], report: PipelineReport
    ) -> List[ArticleProcessed]:
        """Classify, summarize, and persist each unique article."""

        self.logger.info("Step 3-7/8: classifying, mapping entities, and summarizing")
        processed: List[ArticleProcessed] = []
        for article in articles:
            try:
                text = article.raw_text or ""
                company_tags = self.entity_mapper.map_companies(article.title, text)
                classification = self.classifier.classify(
                    title=article.title,
                    text=text,
                    company_tags=company_tags,
                    account_name=article.account_name,
                )
                summary = self.summarizer.summarize(
                    title=article.title,
                    text=text,
                    account_name=article.account_name,
                )
                summary_company_tags = self.entity_mapper.map_companies(
                    "", " ".join(summary.related_companies)
                )
                merged_companies = list(dict.fromkeys(company_tags + summary_company_tags))
                merged_topics = list(
                    dict.fromkeys(classification.topic_tags + summary.related_topics)
                )
                article_processed = ArticleProcessed(
                    article_id=stable_article_id(article.url, article.title, text),
                    url=article.url,
                    title=article.title,
                    account_name=article.account_name,
                    publish_time=article.publish_time,
                    clean_text=text,
                    summary=summary.one_sentence_summary,
                    industry_tags=classification.industry_tags,
                    company_tags=merged_companies,
                    topic_tags=merged_topics,
                    importance_score=max(
                        classification.importance_score,
                        float(summary.importance_score or 0),
                    ),
                    sentiment=summary.sentiment,
                    investment_implications=summary.investment_implications,
                    risks=summary.risks,
                    key_points=summary.key_points,
                    source_type=article.source_type,
                )
                processed.append(article_processed)
                self.sqlite_store.save_processed_article(article_processed)
            except Exception as exc:  # noqa: BLE001 - item-level fallback
                report.failed_items.append(
                    {
                        "title": article.title,
                        "url": article.url,
                        "stage": "process",
                        "error": str(exc),
                    }
                )
                self.logger.warning("Failed to process article %s: %s", article.title, exc)
        return processed

    def _build_llm_client(self):
        """Build a real LLM client when a key is configured, otherwise use MockLLM."""

        return build_llm_client(self.config)
