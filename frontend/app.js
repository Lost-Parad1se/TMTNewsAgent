const state = {
  sourceMode: "manual_url",
  markdown: "",
};

const elements = {
  runButton: document.querySelector("#runButton"),
  topic: document.querySelector("#topic"),
  keywords: document.querySelector("#keywords"),
  days: document.querySelector("#days"),
  maxResults: document.querySelector("#maxResults"),
  urls: document.querySelector("#urls"),
  searchProvider: document.querySelector("#searchProvider"),
  llmProvider: document.querySelector("#llmProvider"),
  browser: document.querySelector("#browser"),
  strategy: document.querySelector("#strategy"),
  enableCdp: document.querySelector("#enableCdp"),
  enableHistory: document.querySelector("#enableHistory"),
  manualUrlSection: document.querySelector("#manualUrlSection"),
  searchSection: document.querySelector("#searchSection"),
  historySection: document.querySelector("#historySection"),
  statusText: document.querySelector("#statusText"),
  sourceText: document.querySelector("#sourceText"),
  windowText: document.querySelector("#windowText"),
  noticeList: document.querySelector("#noticeList"),
  collectedMetric: document.querySelector("#collectedMetric"),
  summarizedMetric: document.querySelector("#summarizedMetric"),
  manualMetric: document.querySelector("#manualMetric"),
  failedMetric: document.querySelector("#failedMetric"),
  markdownPreview: document.querySelector("#markdownPreview"),
  serverDownload: document.querySelector("#serverDownload"),
  clientDownload: document.querySelector("#clientDownload"),
};

document.querySelectorAll("[data-source]").forEach((button) => {
  button.addEventListener("click", () => {
    setSourceMode(button.dataset.source);
  });
});

elements.runButton.addEventListener("click", runResearch);
elements.clientDownload.addEventListener("click", downloadCurrentMarkdown);
elements.days.addEventListener("input", () => {
  elements.windowText.textContent = `${elements.days.value || 3} 天内`;
});

function setSourceMode(sourceMode) {
  state.sourceMode = sourceMode;
  document.querySelectorAll("[data-source]").forEach((button) => {
    button.classList.toggle("active", button.dataset.source === sourceMode);
  });

  elements.manualUrlSection.classList.toggle("hidden", sourceMode !== "manual_url");
  elements.searchSection.classList.toggle("hidden", sourceMode !== "search");
  elements.historySection.classList.toggle("hidden", sourceMode !== "browser_history");

  const labels = {
    manual_url: "手动 URL",
    search: "授权搜索",
    browser_history: "本地历史",
  };
  elements.sourceText.textContent = labels[sourceMode] || sourceMode;
}

function parseList(value) {
  return value
    .split(/[\n,，]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildRequest() {
  return {
    topic: elements.topic.value.trim() || "英伟达、谷歌近期公众号新闻",
    keywords: parseList(elements.keywords.value),
    days: Number(elements.days.value || 3),
    source_mode: state.sourceMode,
    urls: parseList(elements.urls.value),
    search_provider: elements.searchProvider.value,
    llm_provider: elements.llmProvider.value,
    web_access_strategy: elements.strategy.value,
    enable_cdp: elements.enableCdp.checked,
    enable_browser_history: elements.enableHistory.checked,
    browser: elements.browser.value,
    max_results: Number(elements.maxResults.value || 5),
  };
}

async function runResearch() {
  const payload = buildRequest();
  setLoading(true);
  renderNotices([]);
  elements.statusText.textContent = "生成中";
  elements.markdownPreview.textContent = "正在采集、清洗、摘要并生成 Markdown...";

  try {
    const response = await fetch("/research/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "请求失败");
    }

    state.markdown = data.markdown || "";
    elements.statusText.textContent = data.status === "success" ? "已生成" : data.status;
    elements.markdownPreview.textContent = state.markdown || "未生成可预览内容。";
    elements.clientDownload.disabled = !state.markdown;

    if (data.download_url) {
      elements.serverDownload.href = data.download_url;
      elements.serverDownload.classList.remove("disabled");
    }

    const report = data.pipeline_report || {};
    elements.collectedMetric.textContent = report.collected_count || 0;
    elements.summarizedMetric.textContent = report.summarized_count || 0;
    elements.manualMetric.textContent = report.manual_required_count || 0;
    elements.failedMetric.textContent =
      (report.failed_fetch_items || []).length + (report.failed_items || []).length;

    renderNotices(data.warnings || []);
  } catch (error) {
    elements.statusText.textContent = "失败";
    elements.markdownPreview.textContent = "生成失败，请检查输入和后端日志。";
    renderNotices([error.message || String(error)], true);
  } finally {
    setLoading(false);
  }
}

function renderNotices(messages, isError = false) {
  elements.noticeList.innerHTML = "";
  messages.forEach((message) => {
    const item = document.createElement("div");
    item.className = `notice${isError ? " error" : ""}`;
    item.textContent = message;
    elements.noticeList.appendChild(item);
  });
}

function setLoading(isLoading) {
  elements.runButton.disabled = isLoading;
  elements.runButton.textContent = isLoading ? "正在生成..." : "生成 Markdown 报告";
}

function downloadCurrentMarkdown() {
  if (!state.markdown) {
    return;
  }
  const filename = `${safeFilename(elements.topic.value || "research_report")}.md`;
  const blob = new Blob([state.markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function safeFilename(value) {
  return value.replace(/[^\w\u4e00-\u9fff]+/g, "_").replace(/^_+|_+$/g, "") || "report";
}

setSourceMode("manual_url");
