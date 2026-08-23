import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from intent_engine import classify_intent


class IntentEngineTests(unittest.TestCase):
    def test_after_sale_intent(self):
        result = classify_intent("我的电机有明显异响，想报修")
        self.assertEqual(result["intent"], "after_sale")
        self.assertGreater(result["confidence"], 0)
        self.assertTrue(any(e["type"] == "product" for e in result["entities"]))

    def test_order_status_intent(self):
        result = classify_intent("订单A123456什么时候发货")
        self.assertEqual(result["intent"], "order_status")
        self.assertIn("订单", result["matched_keywords"])

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            classify_intent("   ")


if __name__ == "__main__":
    unittest.main()
