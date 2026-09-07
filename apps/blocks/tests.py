from datetime import date, datetime, timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.assets.models import Asset
from apps.blocks.models import BlockWindow
from apps.corridors.models import RailwaySection
from apps.maintenance.models import MaintenanceTask


class UnifiedRecommendationAPITest(APITestCase):

    def setUp(self):
        self.section = RailwaySection.objects.create(
            name="Delhi - Mathura",
            source_station="New Delhi",
            source_station_code="NDLS",
            destination_station="Mathura Jn",
            destination_station_code="MTJ",
            distance_km=141.0,
        )

        self.asset = Asset.objects.create(
            section=self.section,
            name="Delhi Mast OHE-101",
            asset_type="OHE",
            department=Asset.Department.TRACTION,
            criticality=4,
        )

        self.task = MaintenanceTask.objects.create(
            task_id="TMS-TEST-100",
            asset=self.asset,
            description="Inspection of OHE-101",
            severity=3,
            priority=MaintenanceTask.Priority.HIGH,
            due_date=date.today() + timedelta(days=2),
            duration_minutes=60,
            status=MaintenanceTask.Status.PENDING,
        )

    def test_pre_creation_recommendation_post(self):
        """Test unified endpoint discovering feasible slots before creating a block window via POST"""
        url = "/railways/block-windows/recommendation/"
        payload = {
            "task_id": self.task.task_id,
            "date": str(self.task.due_date),
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["task_id"], self.task.task_id)
        self.assertIn("windows", response.data)
        self.assertIn("feasible", response.data)

    def test_pre_creation_recommendation_get(self):
        """Test unified endpoint discovering feasible slots via GET with query params"""
        url = f"/railways/block-windows/recommendation/?task_id={self.task.task_id}&date={self.task.due_date}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["task_id"], self.task.task_id)
        self.assertIn("windows", response.data)

    def test_post_creation_recommendation_get(self):
        """Test unified endpoint evaluating an existing block window"""
        ist = timezone.get_current_timezone()
        start = timezone.make_aware(
            datetime.combine(self.task.due_date, datetime.min.time()) + timedelta(hours=14),
            timezone=ist,
        )
        end = start + timedelta(hours=2)

        bw = BlockWindow.objects.create(
            section=self.section,
            start_time=start,
            end_time=end,
            status=BlockWindow.Status.RESERVED,
        )

        url = f"/railways/block-windows/recommendation/?block_window_id={bw.id}&task_id={self.task.task_id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["block_window_id"], bw.id)
        self.assertIn("current_slot", response.data)
        self.assertIn("has_better_slot", response.data)
        self.assertIn("recommendation_reason", response.data)

    def test_auto_apply_recommendation(self):
        """Test unified endpoint applying AI recommended slot directly via apply=true"""
        ist = timezone.get_current_timezone()
        start = timezone.make_aware(
            datetime.combine(self.task.due_date, datetime.min.time()) + timedelta(hours=14),
            timezone=ist,
        )
        end = start + timedelta(hours=2)

        bw = BlockWindow.objects.create(
            section=self.section,
            start_time=start,
            end_time=end,
            status=BlockWindow.Status.RESERVED,
        )

        url = "/railways/block-windows/recommendation/"
        payload = {
            "block_window_id": bw.id,
            "task_id": self.task.task_id,
            "apply": True,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("applied"))
        self.assertIn("block_window", response.data)

        # Confirm DB was updated
        bw.refresh_from_db()
        self.assertIsNotNone(bw.start_time)
        self.assertIsNotNone(bw.end_time)
