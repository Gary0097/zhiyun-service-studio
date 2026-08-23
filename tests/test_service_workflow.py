import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from service_workflow import ServiceWorkflowStore


class ServiceWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ServiceWorkflowStore(Path(self.tmp.name) / "svc.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_ticket_lifecycle(self):
        ticket = self.store.create_ticket("王先生", "电机异响", "电机", "电机异响")
        self.assertEqual(ticket["status"], "pending_review")
        accepted = self.store.review_ticket(ticket["id"], "accept", "李经理", "张工")
        self.assertEqual(accepted["status"], "accepted")
        self.assertEqual(accepted["recommended_engineer"], "张工")

    def test_reject_reviewer_required(self):
        ticket = self.store.create_ticket("张先生", "控制器烧机", "控制器", "控制器烧机")
        with self.assertRaises(ValueError):
            self.store.review_ticket(ticket["id"], "accept", " ")

    def test_knowledge_artifact(self):
        artifact = self.store.create_knowledge_artifact("知识库", [{"problem": "甲", "solution": "乙"}])
        self.assertEqual(artifact["status"], "pending_review")
        accepted = self.store.review_knowledge(artifact["id"], "accept", "主管")
        self.assertEqual(accepted["status"], "accepted")
        _, media = self.store.export_knowledge(artifact["id"])
        self.assertEqual(media, "application/json")


if __name__ == "__main__":
    unittest.main()
