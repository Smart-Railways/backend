import unittest
import os
import pandas as pd
from apps.blocks.ai_client import RailwayAIClient, AIClientError
import apps.blocks.ai_client as ai_module

class TestEmbeddedAI(unittest.TestCase):

    def test_01_embedded_engine_health(self):
        """Verify that embedded AI engine is available and healthy in-memory."""
        self.assertTrue(RailwayAIClient.is_healthy(), "Embedded AI engine must be healthy")

    def test_02_predict_asset_risk(self):
        """Verify failure risk prediction runs via in-memory model."""
        sample_assets = [
            {"asset_id": 1, "asset_age_years": 4.0, "condition_score": 75.0, "criticality": 3},
            {"asset_id": 2, "asset_age_years": 9.5, "condition_score": 42.0, "criticality": 5},
        ]
        results = RailwayAIClient.predict_asset_risk(sample_assets)
        self.assertEqual(len(results), 2)
        self.assertIn("failure_probability", results[0])
        self.assertIn("model_source", results[0])

    def test_03_optimize_maintenance_blocks(self):
        """Verify CP-SAT block optimizer runs via in-memory engine."""
        tasks = [{
            "task_id": "TEST-TSK-1",
            "section_id": 1,
            "estimated_duration": 90,
            "required_manpower": 4,
            "criticality": 4,
            "priority": "CRITICAL",
            "urgency_score": 0.9,
            "failure_probability": 0.4,
            "predicted_delay_minutes": 10.0
        }]
        block_windows = [{
            "block_id": "BW-TEST-1",
            "section_id": 1,
            "start_time": "2026-09-06 02:00:00",
            "end_time": "2026-09-06 08:00:00"
        }]
        res = RailwayAIClient.optimize_maintenance_blocks(
            tasks=tasks,
            block_windows=block_windows,
            planning_hours=6
        )
        self.assertEqual(res["status"], "OPTIMAL")
        self.assertGreaterEqual(res["allocated_tasks_count"], 1)
        self.assertEqual(res["allocations"][0]["task_id"], "TEST-TSK-1")

    def test_04_http_fallback_offline(self):
        """Verify offline behavior when embedded is disabled and remote is unreachable."""
        orig_prefer = ai_module.PREFER_EMBEDDED_AI
        orig_url = ai_module.AI_SERVICE_URL
        try:
            ai_module.PREFER_EMBEDDED_AI = False
            ai_module.AI_SERVICE_URL = "http://127.0.0.1:59999"
            self.assertFalse(RailwayAIClient.is_healthy())
        finally:
            ai_module.PREFER_EMBEDDED_AI = orig_prefer
            ai_module.AI_SERVICE_URL = orig_url

if __name__ == "__main__":
    unittest.main()
