import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from answer_engine import answer_consult


class AnswerEngineTests(unittest.TestCase):
    def test_faq_answer(self):
        result = answer_consult("电机异响怎么处理")
        self.assertIsNotNone(result["matched_faq"])
        self.assertTrue(result["answer"])

    def test_after_sale_knowledge_hit(self):
        records = [{"problem": "电机异响", "solution": "更换轴承", "tags": ["售后报修"]}]
        result = answer_consult("电机异响怎么修", records)
        self.assertTrue(result.get("knowledge_hit"))

    def test_routed_when_unmatched(self):
        result = answer_consult("帮我看看这个奇怪的文档怎么处理")
        self.assertIsNone(result["matched_faq"])
        self.assertIn("转接", result["answer"])


if __name__ == "__main__":
    unittest.main()
