# TMTNewsAgent

TMTNewsAgent 是一个面向券商研究所互联网/TMT 行业的投研信息整理 Agent 原型。项目支持从公众号文章 URL、本地 CSV、可扩展搜索 API 中获取公开文章线索，完成正文清洗、去重、公司映射、主题分类、LLM 辅助摘要和投研简报生成。

本项目重点是合规、可维护、可扩展的投研工作流演示，不实现绕过登录、验证码、访问限制、反爬机制或高频批量抓取。

## 功能亮点

- 多源信息接入：手动 URL、本地 CSV、搜索 API adapter 骨架。
- 公众号/公开网页正文解析：支持常见 WeChat HTML 字段，如 `rich_media_title`、`js_name`、`js_content`。
- 新闻去重与质量控制：URL、标题归一化和标题相似度去重。
- 互联网/TMT 公司和主题标签体系：内置重点公司别名和行业关键词。
- LLM 辅助摘要：支持 OpenAI-compatible API，缺少 key 时自动使用 MockLLM。
- 投研简报自动生成：输出 Markdown 与 JSON。
- SQLite 存储：保存原始文章、处理结果和简报。
- 失败兜底与日志追踪：单篇失败不会中断整个 pipeline。

## 合规说明

本项目仅用于公开信息整理和学习研究。生产环境应接入合法授权的数据源，不应绕过平台登录、验证码、访问限制或反爬机制。第三方 WeChat/公众号数据工具如 OpenClaw、Apify actor、公众号数据 API 等应作为可替换数据源，不作为强绑定依赖；使用前需确认授权边界、服务条款和数据合规要求。

## 架构流程

```text
Input Sources
  -> Collectors
  -> Extractors
  -> Cleaner
  -> Deduplicator
  -> Classifier / Entity Mapper
  -> LLM Summarizer
  -> Research Brief Writer
  -> SQLite / Markdown / JSON Outputs
```

## 目录结构

```text
TMTNewsAgent/
  config/                 # 数据源、主题、prompt 配置
  data/raw/               # 手工维护 CSV 或输入样例
  data/processed/         # SQLite 数据库
  data/outputs/           # Markdown/JSON 简报与 pipeline_report
  src/
    collectors/           # manual_url / csv / search
    extractors/           # article extractor / html cleaner
    processors/           # dedupe / classify / summarize / report
    llm/                  # replaceable LLM clients
    storage/              # SQLite and file stores
    utils/
  tests/
```

## 快速开始

安装依赖：

```bash
pip install -r requirements.txt
```

复制环境变量模板。没有 LLM key 也可以运行 mock 流程：

```bash
copy .env.example .env
```

运行 CSV demo：

```bash
python -m src.cli --mode csv --topic "AI算力与互联网平台动态" --csv-path data/raw/articles.csv
```

运行手动 URL 模式：

```bash
python -m src.cli --mode manual_url --topic "游戏出海动态" --urls "https://mp.weixin.qq.com/xxx" "https://mp.weixin.qq.com/yyy"
```

运行搜索骨架模式。未配置授权搜索 API 时会返回 mock 结果：

```bash
python -m src.cli --mode search --topic "大模型应用" --keywords "AI算力" "云计算" "腾讯控股" "阿里巴巴"
```

输出文件会写入 `data/outputs/`，包括：

- `brief_<date>_<topic>.md`
- `brief_<date>_<topic>.json`
- `pipeline_report.json`

SQLite 数据库默认写入：

```text
data/processed/tmt_news_agent.db
```

## FastAPI

启动 API：

```bash
uvicorn src.api:app --reload
```

请求示例：

```bash
curl -X POST "http://127.0.0.1:8000/run" ^
  -H "Content-Type: application/json" ^
  -d "{\"mode\":\"csv\",\"topic\":\"AI算力与互联网平台动态\",\"keywords\":[\"AI算力\",\"云计算\",\"腾讯\",\"阿里\"],\"urls\":[],\"csv_path\":\"data/raw/articles.csv\"}"
```

响应示例：

```json
{
  "status": "success",
  "brief_markdown_path": "...",
  "brief_json_path": "...",
  "pipeline_report": {
    "collected_count": 5,
    "extracted_count": 5,
    "deduplicated_count": 5,
    "summarized_count": 5,
    "failed_items": [],
    "output_files": {}
  }
}
```

## LLM 配置

在 `.env` 中配置 OpenAI-compatible API：

```text
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
```

也可以指向 Gemini、Qwen、DeepSeek 或其他兼容 `/chat/completions` 的服务。若没有 `LLM_API_KEY`，系统使用 `MockLLMClient`，保证 CLI、API 和测试流程可以跑通。

## CSV 输入格式

`data/raw/articles.csv` 支持以下字段：

```text
title,url,account_name,publish_time,raw_text
```

示例文件包含 5 条 mock TMT 新闻数据，均已标注为 mock，不伪造真实新闻出处。

## 测试

本项目测试兼容 `unittest`：

```bash
python -m unittest discover -s tests
```

如果已安装 pytest，也可以运行：

```bash
pytest
```

## 后续扩展方向

- 接入合规公众号数据 API、研报、公告、RSS 和新闻 API。
- 增加 RAG 知识库，用于公司历史事件和产业链背景补充。
- 增加前端看板，支持按公司、主题、重要性筛选。
- 增加定时任务和任务队列。
- 增加行业事件数据库和主题热度追踪。
- 增加公司画像、产业链图谱和可视化导出。
- 对接更多 LLM provider，并加入 prompt 版本管理和评估集。

## 简历表述参考

可将项目描述为：

> 构建面向互联网/TMT 行业投研的信息整理 Agent 原型，支持多源公开文章接入、正文清洗、去重、主题分类、公司映射、LLM 摘要和结构化投研简报生成；设计可替换 LLM 与数据源接口，使用 SQLite 记录处理结果，并通过 CLI/FastAPI 提供双入口。
