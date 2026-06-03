"""FastAPI entry point for running the TMT news research agent."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.config import load_config
from src.main import NewsResearchAgent


app = FastAPI(
    title="TMTNewsAgent API",
    description="Compliant public-information workflow for TMT news research briefs.",
    version="0.1.0",
)


class RunRequest(BaseModel):
    """Request body for POST /run."""

    mode: str = Field(..., examples=["csv"])
    topic: str = Field(..., examples=["AI算力与互联网平台动态"])
    keywords: List[str] = Field(default_factory=list)
    urls: List[str] = Field(default_factory=list)
    csv_path: Optional[str] = None
    date: Optional[str] = None


@app.post("/run")
def run_agent(request: RunRequest):
    """Run the research agent and return generated output paths."""

    config = load_config(Path(__file__).resolve().parents[1])
    agent = NewsResearchAgent(config)
    return agent.run(
        mode=request.mode,
        topic=request.topic,
        keywords=request.keywords,
        urls=request.urls,
        csv_path=request.csv_path,
        date=request.date,
    )


@app.get("/health")
def health():
    """Health check endpoint."""

    return {"status": "ok"}
