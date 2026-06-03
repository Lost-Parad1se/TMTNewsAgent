"""FastAPI entry point for running the TMT news research agent."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.config import load_config
from src.llm.provider_registry import supported_provider_names
from src.main import NewsResearchAgent


app = FastAPI(
    title="TMTNewsAgent API",
    description="Compliant public-information workflow for TMT news research briefs.",
    version="0.1.0",
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
if OUTPUT_DIR.exists():
    app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")


class RunRequest(BaseModel):
    """Request body for POST /run."""

    mode: str = Field(..., examples=["csv"])
    topic: str = Field(..., examples=["AI算力与互联网平台动态"])
    keywords: List[str] = Field(default_factory=list)
    urls: List[str] = Field(default_factory=list)
    csv_path: Optional[str] = None
    date: Optional[str] = None
    web_access_strategy: str = "auto"
    enable_cdp: bool = False
    enable_browser_history: bool = False
    browser: str = "all"
    since: str = "7d"
    max_browser_history_results: int = 20
    search_site_filter: Optional[str] = None
    search_recent_days: int = 7
    max_search_results: int = 5
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None


class ResearchWorkbenchRequest(BaseModel):
    """Request body for the frontend research workbench."""

    topic: str = "英伟达、谷歌近期公众号新闻"
    keywords: List[str] = Field(default_factory=lambda: ["英伟达", "谷歌"])
    days: int = 3
    source_mode: str = "manual_url"
    urls: List[str] = Field(default_factory=list)
    search_provider: str = "tavily"
    web_access_strategy: str = "auto"
    enable_cdp: bool = False
    enable_browser_history: bool = False
    browser: str = "all"
    max_results: int = 5
    llm_provider: str = "mock"
    llm_model: Optional[str] = None


@app.post("/run")
def run_agent(request: RunRequest):
    """Run the research agent and return generated output paths."""

    config = load_config(Path(__file__).resolve().parents[1])
    if request.llm_provider:
        config.llm_provider = request.llm_provider
    if request.llm_model:
        config.llm_model = request.llm_model
    agent = NewsResearchAgent(config)
    return agent.run(
        mode=request.mode,
        topic=request.topic,
        keywords=request.keywords,
        urls=request.urls,
        csv_path=request.csv_path,
        date=request.date,
        web_access_strategy=request.web_access_strategy,
        enable_cdp=request.enable_cdp,
        enable_browser_history=request.enable_browser_history,
        browser=request.browser,
        since=request.since,
        max_browser_history_results=request.max_browser_history_results,
        search_site_filter=request.search_site_filter,
        search_recent_days=request.search_recent_days,
        max_search_results=request.max_search_results,
    )


@app.get("/", response_class=HTMLResponse)
def index():
    """Serve the research workbench frontend."""

    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>TMTNewsAgent</h1><p>Frontend is not built yet.</p>")
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


@app.post("/research/report")
def run_research_workbench(request: ResearchWorkbenchRequest):
    """Run a workbench research task and return Markdown content for the frontend."""

    config = load_config(PROJECT_ROOT)
    if request.llm_provider:
        config.llm_provider = request.llm_provider
    if request.llm_model:
        config.llm_model = request.llm_model
    source_mode = request.source_mode
    if source_mode == "search":
        config.sources.setdefault("search", {})["provider"] = request.search_provider

    agent = NewsResearchAgent(config)
    urls = request.urls if source_mode == "manual_url" else []
    result = agent.run(
        mode=source_mode,
        topic=request.topic,
        keywords=request.keywords,
        urls=urls,
        web_access_strategy=request.web_access_strategy,
        enable_cdp=request.enable_cdp,
        enable_browser_history=request.enable_browser_history,
        browser=request.browser,
        since=f"{request.days}d",
        max_browser_history_results=request.max_results,
        search_site_filter="mp.weixin.qq.com/s" if source_mode == "search" else None,
        search_recent_days=request.days,
        max_search_results=request.max_results,
    )

    markdown_path = Path(result["brief_markdown_path"])
    markdown = markdown_path.read_text(encoding="utf-8") if markdown_path.exists() else ""
    warnings = _workbench_warnings(request)
    return {
        **result,
        "markdown": markdown,
        "download_url": f"/outputs/{markdown_path.name}",
        "warnings": warnings,
        "request_summary": {
            "keywords": request.keywords,
            "days": request.days,
            "source_mode": request.source_mode,
            "web_access_strategy": request.web_access_strategy,
            "llm_provider": request.llm_provider,
        },
    }


@app.get("/health")
def health():
    """Health check endpoint."""

    return {"status": "ok"}


@app.get("/llm/providers")
def llm_providers():
    """Return supported LLM provider names for the frontend."""

    return {"providers": supported_provider_names()}


def _workbench_warnings(request: ResearchWorkbenchRequest) -> List[str]:
    """Explain compliant fallback behavior for frontend users."""

    warnings: List[str] = []
    if request.source_mode == "search":
        provider_key = {
            "tavily": "TAVILY_API_KEY",
            "bing": "BING_SEARCH_API_KEY",
        }.get(request.search_provider)
        if provider_key and not os.getenv(provider_key):
            warnings.append(
                f"未检测到 {provider_key}，搜索模式会回退到 mock；请改用手动 URL、本地历史或配置授权搜索 API。"
            )
        if request.search_provider == "bing":
            warnings.append(
                "Bing Search APIs 已不适合作为新演示接入方案；建议使用 Tavily 或其他授权搜索 API。"
            )
    if request.source_mode == "browser_history" and not request.enable_browser_history:
        warnings.append("浏览器历史默认关闭，需要显式启用后才会读取本地匹配项。")
    if request.source_mode == "manual_url" and not request.urls:
        warnings.append("手动 URL 模式需要至少粘贴一个公众号或公开文章链接。")
    if not request.enable_cdp:
        warnings.append("CDP 本地浏览器辅助未启用；公众号静态读取失败时会进入 manual_required。")
    return warnings
