"""Mock LLM client that keeps the MVP runnable without API keys."""

from __future__ import annotations

import json
import re

from src.llm.base import BaseLLMClient


class MockLLMClient(BaseLLMClient):
    """Return deterministic JSON summaries for demos and tests."""

    def generate(self, prompt: str) -> str:
        """Generate a structured mock summary from prompt snippets."""

        title_match = re.search(r"标题：(.+)", prompt)
        title = title_match.group(1).strip() if title_match else "未命名文章"
        text = prompt[-1200:]
        companies = [
            company
            for company in ["腾讯", "阿里", "美团", "字节", "百度", "京东", "小米"]
            if company in text or company in title
        ]
        topics = [
            topic
            for topic in ["AI算力", "云计算", "游戏", "广告营销", "大模型应用", "出海业务"]
            if topic in text or topic in title
        ]
        payload = {
            "one_sentence_summary": f"{title}：该信息为 mock 摘要，需结合原文和公告进一步验证。",
            "key_points": [
                "提取到与互联网/TMT行业相关的业务或产业链线索。",
                "当前结果由 MockLLM 生成，用于演示无 API key 时的完整流程。",
            ],
            "related_companies": companies,
            "related_topics": topics,
            "investment_implications": [
                "关注相关公司收入确认、订单落地和竞争格局变化。",
                "将公众号线索与上市公司公告、财报和行业数据交叉验证。",
            ],
            "risks": [
                "信息来自公开材料或 mock 数据，真实性需进一步验证。",
                "市场预期可能已经提前反映相关主题。",
            ],
            "importance_score": 5.0 + min(len(companies), 3),
            "sentiment": "neutral",
        }
        return json.dumps(payload, ensure_ascii=False)
