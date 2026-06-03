"""Research brief generation in structured JSON and Markdown."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List

from src.models import ArticleProcessed, ResearchBrief


class ReportWriter:
    """Build research briefs from processed articles."""

    def build_brief(self, articles: List[ArticleProcessed], topic: str, date: str) -> ResearchBrief:
        """Create a structured ResearchBrief object."""

        sorted_articles = sorted(articles, key=lambda item: item.importance_score, reverse=True)
        company_updates: Dict[str, List[str]] = defaultdict(list)
        industry_trends: List[str] = []
        risk_alerts: List[str] = []

        for article in sorted_articles:
            summary = article.summary or article.title
            for company in article.company_tags:
                company_updates[company].append(summary)
            for tag in article.industry_tags + article.topic_tags:
                trend = f"{tag}: {summary}"
                if trend not in industry_trends:
                    industry_trends.append(trend)
            risk_alerts.extend(article.risks)

        key_news = [
            f"{article.title} - {article.summary or '待补充摘要'}"
            for article in sorted_articles[:8]
        ]
        executive_summary = self._build_executive_summary(sorted_articles)

        return ResearchBrief(
            date=date,
            topic=topic,
            articles=sorted_articles,
            executive_summary=executive_summary,
            key_news=key_news,
            company_updates=dict(company_updates),
            industry_trends=industry_trends[:10],
            follow_up_questions=self._default_follow_up_questions(),
            risk_alerts=list(dict.fromkeys(risk_alerts))[:10],
        )

    def to_markdown(self, brief: ResearchBrief) -> str:
        """Render a ResearchBrief as Markdown."""

        lines: List[str] = [
            "# TMT/互联网公众号新闻投研简报",
            f"日期：{brief.date}",
            f"主题：{brief.topic}",
            "",
            "## 一、核心摘要",
        ]
        lines.extend(self._bullets(self._split_summary(brief.executive_summary)))

        lines.extend(["", "## 二、重点新闻"])
        for article in brief.articles:
            lines.extend(
                [
                    f"### {article.title}",
                    f"- 来源公众号：{article.account_name or '未知'}",
                    f"- 发布时间：{article.publish_time or '未知'}",
                    f"- 相关公司：{', '.join(article.company_tags) or '待识别'}",
                    f"- 主题标签：{', '.join(article.topic_tags or article.industry_tags) or '待识别'}",
                    f"- 一句话摘要：{article.summary or '待补充'}",
                    f"- 投研关注点：{'; '.join(article.investment_implications) or '需进一步分析'}",
                    f"- 风险/待验证点：{'; '.join(article.risks) or '需进一步验证'}",
                    f"- 原文链接：{article.url or '无'}",
                    "",
                ]
            )

        lines.extend(["## 三、公司动态"])
        if brief.company_updates:
            for company, updates in brief.company_updates.items():
                lines.append(f"### {company}")
                lines.extend(self._bullets(updates))
                lines.append("- 可能影响：需结合公告、财报和行业数据进一步验证。")
        else:
            lines.append("- 暂未识别到重点公司动态。")

        lines.extend(["", "## 四、产业链/主题趋势"])
        lines.extend(self._bullets(brief.industry_trends or ["暂无明确产业链趋势，建议补充更多样本。"]))

        lines.extend(["", "## 五、后续跟踪问题"])
        lines.extend(self._bullets(brief.follow_up_questions))

        lines.extend(["", "## 六、风险提示"])
        default_risks = [
            "信息源可靠性风险",
            "转载失真风险",
            "政策变化风险",
            "竞争格局变化风险",
            "估值已反映风险",
        ]
        lines.extend(self._bullets(brief.risk_alerts or default_risks))
        return "\n".join(lines).strip() + "\n"

    def _build_executive_summary(self, articles: List[ArticleProcessed]) -> str:
        """Build a compact top-line summary."""

        if not articles:
            return "本次运行未获得可用文章，建议补充 CSV 或手动 URL。"
        summaries = [article.summary or article.title for article in articles[:5]]
        return "\n".join(summaries)

    @staticmethod
    def _split_summary(summary: str) -> List[str]:
        """Split an executive summary into 3-5 bullets."""

        lines = [line.strip("- ") for line in summary.splitlines() if line.strip()]
        return lines[:5] or ["暂无核心摘要。"]

    @staticmethod
    def _bullets(items: Iterable[str]) -> List[str]:
        """Render items as Markdown bullets."""

        return [f"- {item}" for item in items]

    @staticmethod
    def _default_follow_up_questions() -> List[str]:
        """Return research follow-up questions suitable for TMT analysts."""

        return [
            "相关订单、产品或政策是否会影响公司收入确认节奏？",
            "产业链上下游是否出现价格或供需变化？",
            "是否已有上市公司公告、财报或监管文件可以交叉验证？",
            "市场预期是否已经充分反映该主题？",
            "竞争对手是否出现类似动作，行业格局是否变化？",
            "该事件对毛利率、费用率或资本开支有何潜在影响？",
            "后续有哪些时间点需要持续跟踪？",
        ]
