import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from ticket_engine import recommend_engineer, route_ticket


class TicketEngineTests(unittest.TestCase):
    def test_route_motor(self):
        result = route_ticket({"fault_type": "电机异响", "description": "电机有异响", "product": "电机"})
        self.assertEqual(result["team"], "电机组")

    def test_recommend_engineer(self):
        engineers = [{"name": "张工", "skills": ["电机", "异响"], "active_tickets": 0}]
        result = recommend_engineer({"fault_type": "电机异响", "description": "异响", "product": "电机"}, engineers)
        self.assertEqual(result["recommendations"][0]["name"], "张工")
        self.assertGreater(result["recommendations"][0]["score"], 60)


if __name__ == "__main__":
    unittest.main()
