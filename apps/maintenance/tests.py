from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.assets.models import Asset
from apps.corridors.models import RailwaySection
from apps.maintenance.models import MaintenanceTask
from apps.maintenance.models import MaintenanceLog


class MaintenanceLifecycleAPITest(APITestCase):
    def setUp(self):
        section = RailwaySection.objects.create(
            name="Delhi - Agra",
            source_station="New Delhi",
            source_station_code="NDLS",
            destination_station="Agra Cantt",
            destination_station_code="AGC",
            distance_km=195,
        )
        asset = Asset.objects.create(
            section=section,
            name="Track circuit 1",
            asset_type="TRACK_CIRCUIT",
            department=Asset.Department.SNT,
            criticality=3,
        )
        self.task = MaintenanceTask.objects.create(
            task_id="MNT-LIFECYCLE-1",
            asset=asset,
            description="Inspect track circuit",
            severity=3,
            priority=MaintenanceTask.Priority.HIGH,
            due_date=timezone.localdate() + timedelta(days=1),
            duration_minutes=45,
            status=MaintenanceTask.Status.SCHEDULED,
        )
        self.base_url = f"/railways/maintenance-tasks/{self.task.id}"

    def test_start_requires_completed_checklist_and_activates_task(self):
        rejected = self.client.post(
            f"{self.base_url}/start/",
            {"checklist": [{"item": "PPE", "completed": False}]},
            format="json",
        )
        self.assertEqual(rejected.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(
            f"{self.base_url}/start/",
            {"checklist": [{"item": "PPE", "completed": True}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["task_status"], MaintenanceTask.Status.ACTIVE)
        self.assertEqual(response.data["checklist"][0]["item"], "PPE")
        self.assertTrue(
            MaintenanceLog.objects.filter(
                task=self.task, event=MaintenanceLog.Event.STARTED
            ).exists()
        )

    def test_complete_and_cancel_require_remarks(self):
        self.task.status = MaintenanceTask.Status.ACTIVE
        self.task.save()

        rejected_completion = self.client.post(
            f"{self.base_url}/complete/", {"remark": " "}, format="json"
        )
        self.assertEqual(rejected_completion.status_code, status.HTTP_400_BAD_REQUEST)

        completed = self.client.post(
            f"{self.base_url}/complete/", {"remark": "Repair verified"}, format="json"
        )
        self.assertEqual(completed.status_code, status.HTTP_200_OK)
        self.assertEqual(completed.data["task_status"], MaintenanceTask.Status.COMPLETED)
        self.assertTrue(
            MaintenanceLog.objects.filter(
                task=self.task,
                event=MaintenanceLog.Event.COMPLETED,
                remark="Repair verified",
            ).exists()
        )

        another_task = MaintenanceTask.objects.create(
            task_id="MNT-LIFECYCLE-2",
            asset=self.task.asset,
            description="Second inspection",
            severity=2,
            priority=MaintenanceTask.Priority.LOW,
            due_date=timezone.localdate() + timedelta(days=1),
            duration_minutes=30,
        )
        cancelled = self.client.post(
            f"/railways/maintenance-tasks/{another_task.id}/cancel/",
            {"remark": "Asset replaced"},
            format="json",
        )
        self.assertEqual(cancelled.status_code, status.HTTP_200_OK)
        self.assertEqual(cancelled.data["task_status"], MaintenanceTask.Status.CANCELLED)

        logs = self.client.get(f"/railways/maintenance-logs/?task_code={another_task.task_id}")
        self.assertEqual(logs.status_code, status.HTTP_200_OK)
        self.assertEqual(logs.data[0]["event"], MaintenanceLog.Event.CANCELLED)

    def test_overdue_active_task_becomes_delayed(self):
        self.task.due_date = timezone.localdate() - timedelta(days=1)
        self.task.status = MaintenanceTask.Status.ACTIVE
        # Use queryset update to model an active task crossing its deadline;
        # save() would immediately apply the same overdue rule.
        MaintenanceTask.objects.filter(pk=self.task.pk).update(
            due_date=self.task.due_date,
            status=MaintenanceTask.Status.ACTIVE,
        )

        response = self.client.get(f"{self.base_url}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["task_status"], MaintenanceTask.Status.DELAYED)
        self.assertTrue(response.data["is_delayed"])
