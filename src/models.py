"""Pydantic models used across the TMT news research workflow."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ArticleRaw(BaseModel):
    """Raw article metadata and content collected from a source."""

    source_type: str
    url: Optional[str] = None
    final_url: Optional[str] = None
    title: str
    author: Optional[str] = None
    publish_time: Optional[str] = None
    account_name: Optional[str] = None
    raw_html: Optional[str] = None
    raw_text: Optional[str] = None
    fetched_at: str
    fetch_status: str = "success"
    fetch_strategy: Optional[str] = None
    fetch_metadata: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    quality_flags: List[str] = Field(default_factory=list)


class ArticleProcessed(BaseModel):
    """Cleaned, tagged, summarized article ready for report generation."""

    article_id: str
    url: Optional[str] = None
    title: str
    account_name: Optional[str] = None
    publish_time: Optional[str] = None
    clean_text: str
    summary: Optional[str] = None
    industry_tags: List[str] = Field(default_factory=list)
    company_tags: List[str] = Field(default_factory=list)
    topic_tags: List[str] = Field(default_factory=list)
    importance_score: float = 0.0
    sentiment: Optional[str] = None
    investment_implications: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    key_points: List[str] = Field(default_factory=list)
    source_type: Optional[str] = None


class ResearchBrief(BaseModel):
    """Structured research brief assembled from processed articles."""

    date: str
    topic: str
    articles: List[ArticleProcessed] = Field(default_factory=list)
    executive_summary: str
    key_news: List[str] = Field(default_factory=list)
    company_updates: Dict[str, List[str]] = Field(default_factory=dict)
    industry_trends: List[str] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(default_factory=list)
    risk_alerts: List[str] = Field(default_factory=list)


class ClassificationResult(BaseModel):
    """Rule-based and optional LLM-assisted classification output."""

    industry_tags: List[str] = Field(default_factory=list)
    topic_tags: List[str] = Field(default_factory=list)
    importance_score: float = 0.0


class SummaryResult(BaseModel):
    """Normalized LLM summary payload for a single article."""

    one_sentence_summary: str = ""
    key_points: List[str] = Field(default_factory=list)
    related_companies: List[str] = Field(default_factory=list)
    related_topics: List[str] = Field(default_factory=list)
    investment_implications: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    importance_score: float = 0.0
    sentiment: str = "neutral"


class PipelineReport(BaseModel):
    """Operational report for one agent run."""

    collected_count: int = 0
    extracted_count: int = 0
    deduplicated_count: int = 0
    summarized_count: int = 0
    fetch_strategy_stats: Dict[str, int] = Field(default_factory=dict)
    cdp_used_count: int = 0
    manual_required_count: int = 0
    failed_fetch_items: List[Dict[str, Any]] = Field(default_factory=list)
    failed_items: List[Dict[str, Any]] = Field(default_factory=list)
    output_files: Dict[str, str] = Field(default_factory=dict)


def model_to_dict(model: BaseModel) -> Dict[str, Any]:
    """Return a plain dictionary for either Pydantic v1 or v2 models."""

    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()
