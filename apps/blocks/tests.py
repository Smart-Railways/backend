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

    def test_get_block_window_by_id_includes_task_info(self):
        """Test GET /railways/block-windows/{id}/ returns task_id and task details"""
        ist = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.now(), timezone=ist)
        end = start + timedelta(hours=2)

        bw = BlockWindow.objects.create(
            section=self.section,
            task=self.task,
            start_time=start,
            end_time=end,
            status=BlockWindow.Status.RESERVED,
        )

        response = self.client.get(f"/railways/block-windows/{bw.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["task_id"], self.task.task_id)
        self.assertEqual(response.data["task_code"], self.task.task_id)
        self.assertEqual(response.data["task"], self.task.id)
        self.assertIn("task_details", response.data)
        self.assertIn("task_asset_name", response.data)

    def test_get_block_windows_filter_by_task_id(self):
        """Test GET /railways/block-windows/?task_id=... returns task's block windows"""
        ist = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.now(), timezone=ist)
        end = start + timedelta(hours=2)

        bw = BlockWindow.objects.create(
            section=self.section,
            task=self.task,
            start_time=start,
            end_time=end,
            status=BlockWindow.Status.RESERVED,
        )

        response = self.client.get(f"/railways/block-windows/?task_id={self.task.task_id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], bw.id)
        self.assertEqual(response.data[0]["task_id"], self.task.task_id)

    def test_get_block_window_by_task_endpoint(self):
        """Test GET /railways/block-windows/by-task/{task_id}/ returns the block window"""
        ist = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.now(), timezone=ist)
        end = start + timedelta(hours=2)

        bw = BlockWindow.objects.create(
            section=self.section,
            task=self.task,
            start_time=start,
            end_time=end,
            status=BlockWindow.Status.RESERVED,
        )

        response = self.client.get(f"/railways/block-windows/by-task/{self.task.task_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], bw.id)
        self.assertEqual(response.data["task_id"], self.task.task_id)
        self.assertEqual(response.data["task_code"], self.task.task_id)

    def test_delete_maintenance_task_cascades_block_window(self):
        """Test deleting a MaintenanceTask cascades and deletes its linked BlockWindow"""
        ist = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.now(), timezone=ist)
        end = start + timedelta(hours=2)

        bw = BlockWindow.objects.create(
            section=self.section,
            task=self.task,
            start_time=start,
            end_time=end,
            status=BlockWindow.Status.RESERVED,
        )
        bw_id = bw.id
        self.assertTrue(BlockWindow.objects.filter(id=bw_id).exists())

        # Delete the maintenance task via API
        response = self.client.delete(f"/railways/maintenance-tasks/{self.task.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify block window was cascade deleted
        self.assertFalse(BlockWindow.objects.filter(id=bw_id).exists())

    def test_put_block_window_by_task_endpoint(self):
        """Test PUT /railways/block-windows/by-task/{task_id}/ updates the block window"""
        ist = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.now(), timezone=ist)
        end = start + timedelta(hours=2)

        bw = BlockWindow.objects.create(
            section=self.section,
            task=self.task,
            start_time=start,
            end_time=end,
            status=BlockWindow.Status.AVAILABLE,
        )

        new_start = start + timedelta(hours=4)
        new_end = new_start + timedelta(hours=2)
        payload = {
            "start_time": new_start.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": new_end.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "RESERVED",
        }

        response = self.client.put(
            f"/railways/block-windows/by-task/{self.task.task_id}/",
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], bw.id)
        self.assertEqual(response.data["status"], "RESERVED")
        self.assertEqual(response.data["task_id"], self.task.task_id)

        # Confirm DB updated
        bw.refresh_from_db()
        self.assertEqual(bw.status, BlockWindow.Status.RESERVED)
        self.assertEqual(bw.start_time.strftime("%Y-%m-%d %H:%M:%S"), payload["start_time"])

    def test_create_block_window_links_task_id(self):
        """Test POST /railways/block-windows/ with task_id links the task and marks it SCHEDULED"""
        ist = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.now(), timezone=ist)
        end = start + timedelta(hours=2)

        payload = {
            "section": self.section.id,
            "task_id": self.task.task_id,
            "start_time": start.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": end.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "RESERVED",
        }
        response = self.client.post("/railways/block-windows/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["task_id"], self.task.task_id)
        self.assertEqual(response.data["task"], self.task.id)

        # Confirm task transitioned to SCHEDULED
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, MaintenanceTask.Status.SCHEDULED)

    def test_create_block_window_invalid_task_id_fails(self):
        """Test POST /railways/block-windows/ with non-existent task_id returns 400 Bad Request"""
        ist = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.now(), timezone=ist)
        end = start + timedelta(hours=2)

        payload = {
            "section": self.section.id,
            "task_id": "NON-EXISTENT-TASK-999",
            "start_time": start.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": end.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "RESERVED",
        }
        response = self.client.post("/railways/block-windows/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("task_id", response.data)



