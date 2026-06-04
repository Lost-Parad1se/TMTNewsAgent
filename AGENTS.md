# AGENTS.md

## 项目定位

TMTNewsAgent 是一个面向券商研究所互联网/TMT 行业的投研信息整理 Agent 原型。它从手动 URL、本地 CSV、搜索 adapter 骨架、本地浏览器历史匹配等来源获取文章线索，经过正文清洗、去重、公司映射、主题分类、LLM 辅助摘要，最终生成 Markdown/JSON 投研简报，并把原始文章、处理结果和简报写入 SQLite。

项目核心原则是合规、可维护、可扩展。不要实现或引入绕过登录、验证码、访问限制、反爬策略、付费墙或高频批量抓取的逻辑。

## 当前代码状态

- 已有 MVP 主流程：采集 -> 清洗 -> 去重 -> 分类/公司映射 -> 摘要 -> 简报生成 -> SQLite/文件输出。
- 已新增稳健网页读取能力：`static`、`jina`、可选本地 `cdp`、本地浏览器历史匹配骨架。
- 已新增 FastAPI 托管前端：`frontend/index.html`、`frontend/styles.css`、`frontend/app.js`，用于生成 Markdown 投研报告。
- `manual_url` 模式已通过 `WebAccessLayer` 获取正文，不再直接调用旧的 `ArticleExtractor.fetch_article`。
- `search` 模式默认仍以 mock 为主；推荐配置 `TAVILY_API_KEY` 并选择 provider `tavily`，可通过授权 Tavily Search API 获取候选 URL，再交给 `WebAccessLayer` 抓取。`BING_SEARCH_API_KEY` 仅作为兼容选项保留。
- `browser_history` 模式默认关闭，必须显式传 `--enable-browser-history`。
- 当前项目使用 `.gitignore` 忽略 `.venv/`、`__pycache__/`、真实 `.env` 等运行产物。

## 重要目录

```text
config/
  sources.yaml          # 数据源、搜索 provider、请求策略
  topics.yaml           # TMT 公司别名、主题关键词
  prompts.yaml          # LLM prompt
  web_access.yaml       # 网页读取配置

data/
  raw/articles.csv      # CSV demo 输入
  processed/            # SQLite 数据库目录
  outputs/              # 简报与 pipeline_report 输出

references/site_patterns/
  mp.weixin.qq.com.md   # 微信公众号站点模式、陷阱、合规边界
  generic_article.md    # 普通文章页抽取模式

src/
  collectors/           # csv / manual_url / search collector
  extractors/           # HTML 清洗和旧文章抽取器
  web_access/           # 网页读取与本地辅助能力
  processors/           # 去重、分类、实体映射、摘要、简报
  llm/                  # MockLLM 与 OpenAI-compatible 客户端
  storage/              # SQLite 与文件输出
  utils/                # 日志、时间、文本工具

frontend/
  index.html            # 行研工作台页面
  styles.css            # 工作台视觉样式
  app.js                # 前端表单、请求、Markdown 下载逻辑

tests/                  # unittest 测试
```

## 核心入口

- CLI 入口：`src/cli.py`
- API 入口：`src/api.py`
- 前端入口：启动 FastAPI 后访问 `http://127.0.0.1:8000/`
- 主编排类：`src/main.py` 的 `NewsResearchAgent`
- 配置加载：`src/config.py` 的 `load_config`
- 数据模型：`src/models.py`

`NewsResearchAgent.run()` 是主入口，支持参数：

- `mode`: `csv` / `manual_url` / `search` / `browser_history`
- `topic`: 简报主题
- `keywords`: 搜索或浏览器历史关键词
- `urls`: 手动 URL
- `csv_path`: CSV 路径
- `date`: 简报日期
- `web_access_strategy`: `auto` / `static` / `jina` / `cdp` / `manual`
- `enable_cdp`: 是否允许本地 CDP proxy
- `enable_browser_history`: 是否允许读取本地浏览器历史
- `browser`: `chrome` / `edge` / `all`
- `since`: 浏览器历史时间窗，例如 `1d`、`7d`、`30d`
- `max_browser_history_results`: 历史匹配上限

前端工作台接口为 `POST /research/report`，会返回：

- `markdown`: Markdown 报告内容
- `download_url`: 服务端 `.md` 文件 URL
- `pipeline_report`: 采集、失败、manual_required 等统计
- `warnings`: 搜索 API 未配置、CDP 未开启、缺少 URL 等合规提示

前端可传 `llm_provider`，用于在已配置 `.env` key 的前提下切换 `mock/gemini/qwen/deepseek/glm/openai-compatible`；不要在前端收集或发送 API Key。

## 数据流

1. `_collect()` 根据 `mode` 选择 collector。
2. 采集结果是 `ArticleRaw` 列表。
3. `_apply_fetch_report()` 根据 `ArticleRaw.fetch_strategy/fetch_status` 生成抓取统计。
4. `_extract_and_clean()` 清洗 `raw_text/raw_html`。`success` 和 `partial` 会继续处理；`failed/manual_required` 会进入失败项。
5. `Deduplicator` 去重。
6. `EntityMapper`、classifier、summarizer 处理文章。
7. `ReportWriter` 生成 `ResearchBrief`。
8. `FileStore` 输出 Markdown/JSON，`SQLiteStore` 保存数据。

## 关键模型

`ArticleRaw` 是采集层输出：

- `source_type`: 来源，如 `csv`、`manual_url`、`search`、`browser_history`
- `url/final_url/title/raw_html/raw_text`
- `fetch_status`: `success` / `failed` / `partial` / `manual_required`
- `fetch_strategy`: `static` / `jina` / `cdp` / `manual_required` / `browser_history`
- `fetch_metadata`: HTTP 状态、Jina URL、CDP tab id、历史访问时间等附加信息
- `quality_flags`: 低质量、mock、策略标签等

`PipelineReport` 会记录：

- `collected_count`
- `extracted_count`
- `deduplicated_count`
- `summarized_count`
- `fetch_strategy_stats`
- `cdp_used_count`
- `manual_required_count`
- `failed_fetch_items`
- `failed_items`
- `output_files`

## 网页读取与本地辅助

核心文件：

- `src/web_access/base.py`: `FetchResult` 和 `BaseFetcher`
- `src/web_access/strategy_router.py`: `AccessStrategyRouter`、`WebAccessLayer`
- `src/web_access/static_fetcher.py`: 单次静态 HTTP 获取
- `src/web_access/jina_fetcher.py`: Jina Reader 获取 markdown
- `src/web_access/cdp_fetcher.py`: 显式开启的本地 CDP proxy 获取
- `src/web_access/browser_history_collector.py`: 显式开启的本地浏览器历史关键词匹配
- `src/web_access/validators.py`: URL 类型、标题/正文抽取、访问限制文本识别

默认策略：

- 普通文章页：`["jina", "static"]`
- 微信公众号文章：`["static", "manual_required"]`
- 微信公众号文章且 `enable_cdp=true`：`["static", "cdp_optional", "manual"]`
- PDF URL：`["static"]`
- 空 URL/关键词：不在 router 中处理，应交给 `SearchCollector`

注意事项：

- 不要裁剪微信公众号 URL 的 query 参数。
- `JinaFetcher.normalize_jina_url()` 的格式是给原 URL 前置 `https://r.jina.ai/`，例如 `https://r.jina.ai/https://example.com/path`，不要重复拼接。
- `StaticFetcher` 不做高频重试，HTTP 错误返回 `FetchResult(status="failed")`，不能中断 pipeline。
- `CDPFetcher` 默认关闭，只检测 `http://localhost:3456` proxy 是否可用，不启动第三方工具。
- CDP 只操作自己创建的 tab，读取后关闭，不操作用户已有 tab。
- `fetch_many()` 默认单线程；如需低并发，可在 `config/web_access.yaml` 设置小的 `max_concurrency`，内部最多使用 4 个 worker。

## 浏览器历史能力

`BrowserHistoryCollector` 位于 `src/web_access/browser_history_collector.py`。

- 默认关闭。
- 只有 CLI/API 显式开启 `enable_browser_history` 才读取。
- 只匹配关键词，只返回匹配到的 `url`、`title`、`last_visit_time`、`browser`。
- 不保存完整历史。
- 目前支持 Chromium 系浏览器历史 SQLite 路径，Windows 优先 Edge/Chrome，macOS 支持 Edge/Chrome 默认 Profile。
- 当前返回的是 `ArticleRaw` 壳数据，正文仍需 WebAccessLayer、CSV 或手动正文补充。

## Collector 说明

- `CSVCollector`: 读取本地 CSV，字段为 `title,url,account_name,publish_time,raw_text`。
- `ManualURLCollector`: 接收用户 URL，调用 `WebAccessLayer.fetch_many()`。
- `SearchCollector`: 当前为 mock 搜索骨架；真实 provider adapter 预留在 `_collect_from_adapter()`。
- `SearchCollector`: provider 为 `tavily` 且存在 `TAVILY_API_KEY` 时，会调用授权 Tavily Search API，小批量获取候选 URL；provider 为 `bing` 且存在 `BING_SEARCH_API_KEY` 时，会调用 Bing Web Search API 兼容路径。
- 搜索 provider key 映射：`TAVILY_API_KEY`、`SERPAPI_API_KEY`、`BING_SEARCH_API_KEY`、`SOGOU_WECHAT_API_KEY`。

## LLM 行为

- LLM 入口是 `src/llm/factory.py` 的 `build_llm_client()`。
- Provider 默认值来自 `src/llm/provider_registry.py`，统一走 `OpenAICompatibleClient`。
- 支持 `LLM_PROVIDER=mock/gemini/qwen/deepseek/glm/kimi/openai-compatible`。
- Gemini 使用 `GEMINI_API_KEY`，默认 base URL 为 `https://generativelanguage.googleapis.com/v1beta/openai`。
- Qwen 使用 `DASHSCOPE_API_KEY`，默认 base URL 为 `https://dashscope.aliyuncs.com/compatible-mode/v1`。
- DeepSeek 使用 `DEEPSEEK_API_KEY`，默认 base URL 为 `https://api.deepseek.com`。
- GLM 使用 `ZHIPUAI_API_KEY`，默认 base URL 为 `https://open.bigmodel.cn/api/paas/v4`。
- Kimi 使用 `MOONSHOT_API_KEY`，默认 base URL 为 `https://api.moonshot.cn/v1`。
- 自定义 OpenAI-compatible provider 使用 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`。
- 没有配置对应 key 且 `LLM_FALLBACK_TO_MOCK=true` 时，回退 `MockLLMClient`，保证 demo 和测试不依赖真实 LLM。
- `.env.example` 只放模板；真实 `.env` 不应提交。

## 常用命令

安装依赖：

```bash
pip install -r requirements.txt
```

推荐在本地虚拟环境运行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

运行 CSV demo：

```bash
.venv/bin/python -m src.cli --mode csv --topic "AI算力与互联网平台动态" --csv-path data/raw/articles.csv
```

运行手动 URL：

```bash
.venv/bin/python -m src.cli \
  --mode manual_url \
  --topic "AI算力动态" \
  --urls "https://example.com/news/ai-compute" \
  --web-access-strategy auto
```

显式启用本地浏览器历史匹配：

```bash
.venv/bin/python -m src.cli \
  --mode browser_history \
  --topic "AI算力近期动态" \
  --keywords "AI算力" "光模块" "英伟达" \
  --enable-browser-history \
  --since 7d
```

启动 API：

```bash
.venv/bin/uvicorn src.api:app --reload
```

打开前端：

```text
http://127.0.0.1:8000/
```

前端默认任务是“英伟达、谷歌近期公众号新闻”，时间窗口默认 3 天。实际搜索公众号文章建议配置 `TAVILY_API_KEY` 并选择“授权搜索”；没有授权搜索 API 时，使用手动 URL、本地历史或 CSV/手动正文。

运行测试：

```bash
.venv/bin/python -m unittest discover -s tests
```

也可以：

```bash
.venv/bin/pytest
```

## 当前测试覆盖

- `tests/test_classifier.py`: 公司别名映射和主题分类。
- `tests/test_deduplicator.py`: 去重逻辑。
- `tests/test_report_writer.py`: Markdown 简报生成。
- `tests/test_strategy_router.py`: Web Access 策略路由、CDP 禁用时不调用、微信 URL query 不裁剪。
- `tests/test_fetch_result.py`: `FetchResult` 到 `ArticleRaw` 的转换、失败不打断收集、Jina URL 归一化。
- `tests/test_site_patterns.py`: 站点模式文档里的关键合规条款。

最后一次已知验证：

```text
.venv/bin/python -m unittest discover -s tests
14 tests OK
```

运行测试时，macOS/Xcode Python 可能出现 urllib3 与 LibreSSL 的兼容警告；当前不影响测试通过。

## 合规红线

后续 Agent 修改项目时必须遵守：

- 不绕过登录。
- 不绕过验证码。
- 不绕过访问限制、反爬策略或付费墙。
- 不进行高频批量抓取。
- 不默认启用 CDP。
- 不默认读取浏览器历史。
- 不保存完整浏览器历史。
- 不裁剪微信公众号 URL query 参数。
- 静态请求失败、低质量正文或提示“内容不存在/访问受限”时，不要直接断言文章不存在，应进入手动正文、CSV 或合规数据源兜底。

## 开发建议

- 新增数据源时优先放在 `src/collectors/`，并保持输出为 `ArticleRaw`。
- 新增网页读取方式时优先扩展 `src/web_access/`，通过 `FetchResult` 返回结果，不要让异常中断 pipeline。
- 新增平台规则时写入 `references/site_patterns/`，并补对应测试。
- 修改 pipeline 时关注 `PipelineReport`，确保失败项和策略统计仍可解释。
- 尽量保持配置可选、默认保守，避免把实验能力变成默认行为。
- 如果新增真实搜索 provider，必须检查授权、速率限制、服务条款和 key 管理。
- 修改前端时保持工作台风格，优先信息密度、扫描效率、清晰状态和可下载产物，不要做营销页或大面积装饰性 hero。
- 如果新增 LLM provider，优先复用 OpenAI-compatible 接口或在 `src/llm/` 中新增小型 adapter。
- 不要提交 `.venv/`、`__pycache__/`、真实 `.env`、临时日志或大体量运行缓存。

## 已知可扩展方向

- 接入合规新闻 API、RSS、公告、研报或授权公众号数据 API。
- 将 `SearchCollector._collect_from_adapter()` 实现为可插拔 provider。
- 为普通文章页增加 JSON-LD 元数据抽取。
- 为浏览器历史匹配结果增加“再经 WebAccessLayer 读取正文”的可选二阶段流程。
- 增加 RAG 知识库，用于公司历史事件和产业链背景补充。
- 增加前端看板、定时任务、任务队列、主题热度追踪和可视化导出。
