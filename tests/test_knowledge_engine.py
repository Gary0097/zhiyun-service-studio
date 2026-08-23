import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from knowledge_engine import extract_knowledge, optimize_knowledge


class KnowledgeEngineTests(unittest.TestCase):
    def test_extract_dedupe(self):
        records = [
            {"fault_type": "电机异响", "cause": "轴承磨损", "solution": "更换轴承", "product": "电机"},
            {"fault_type": "电机异响", "cause": "轴承磨损", "solution": "更换轴承", "product": "电机"},
        ]
        result = extract_knowledge(records)
        self.assertEqual(result["count"], 1)
        self.assertTrue(result["entries"][0]["tags"])

    def test_optimize_scores(self):
        entries = [{"problem": "甲", "solution": "方案", "cause": "原因", "tags": ["售后报修", "质量缺陷"]}]
        result = optimize_knowledge(entries)
        self.assertEqual(result["total"], 1)
        self.assertGreaterEqual(result["entries"][0]["score"], 80)


if __name__ == "__main__":
    unittest.main()
