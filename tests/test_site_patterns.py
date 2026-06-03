"""Tests for site pattern reference docs."""

from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SitePatternsTest(unittest.TestCase):
    """Ensure compliance notes stay visible in site pattern docs."""

    def test_wechat_pattern_documents_key_boundaries(self):
        text = (
            PROJECT_ROOT / "references" / "site_patterns" / "mp.weixin.qq.com.md"
        ).read_text(encoding="utf-8")

        self.assertIn("不裁剪 query 参数", text)
        self.assertIn("静态请求失败", text)
        self.assertIn("不绕过登录、验证码、访问限制", text)
        self.assertIn("手动粘贴正文", text)

    def test_generic_article_pattern_documents_fallback_order(self):
        text = (
            PROJECT_ROOT / "references" / "site_patterns" / "generic_article.md"
        ).read_text(encoding="utf-8")

        self.assertIn("meta", text)
        self.assertIn("<article>", text)
        self.assertIn("JSON-LD", text)
        self.assertIn("单篇失败不得中断 pipeline", text)


if __name__ == "__main__":
    unittest.main()
