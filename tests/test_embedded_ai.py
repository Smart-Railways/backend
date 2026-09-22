import unittest

from apps.blocks.ai_client import RailwayAIClient


class EmbeddedRailwayAITest(unittest.TestCase):
    def test_engine_health(self):
        self.assertTrue(RailwayAIClient.is_healthy())

    def test_risk_prediction(self):
        results = RailwayAIClient.predict_asset_risk([
            {
                "asset_id": 1,
                "asset_age_years": 4.0,
                "condition_score": 75.0,
                "criticality": 3,
            }
        ])
        self.assertEqual(len(results), 1)
        self.assertIn("failure_probability", results[0])

    def test_block_optimization(self):
        result = RailwayAIClient.optimize_maintenance_blocks(
            tasks=[{
                "task_id": "TEST-1",
                "section_id": 1,
                "estimated_duration": 60,
                "required_manpower": 2,
                "criticality": 4,
                "priority": "HIGH",
                "urgency_score": 0.7,
                "failure_probability": 0.1,
                "predicted_delay_minutes": 0,
            }],
            block_windows=[{"block_id": "BW-1", "section_id": 1}],
        )
        self.assertIn(result["status"], {"OPTIMAL", "INFEASIBLE"})
