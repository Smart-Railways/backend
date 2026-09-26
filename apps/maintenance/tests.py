from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.assets.models import Asset
from apps.blocks.models import BlockWindow
from apps.corridors.models import RailwaySection
from apps.maintenance.models import MaintenanceBatch, MaintenanceLog, MaintenanceTask


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

    def test_deleting_a_task_does_not_create_an_audit_log(self):
        response = self.client.delete(f"{self.base_url}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            MaintenanceLog.objects.filter(task_code=self.task.task_id).exists()
        )

    def test_complete_and_cancel_require_remarks(self):
        self.task.status = MaintenanceTask.Status.ACTIVE
        self.task.started_at = timezone.now()
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

    def test_shared_batch_lifecycle_synchronizes_all_linked_tasks(self):
        second_asset = Asset.objects.create(
            section=self.task.asset.section,
            name="Track circuit 2",
            asset_type="TRACK_CIRCUIT",
            department=Asset.Department.SNT,
            criticality=3,
        )
        second_task = MaintenanceTask.objects.create(
            task_id="MNT-LIFECYCLE-BATCH-2",
            asset=second_asset,
            description="Inspect second track circuit",
            severity=3,
            priority=MaintenanceTask.Priority.HIGH,
            due_date=self.task.due_date,
            duration_minutes=30,
            status=MaintenanceTask.Status.SCHEDULED,
        )
        block_window = BlockWindow.objects.create(
            section=self.task.asset.section,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(minutes=90),
            status=BlockWindow.Status.RESERVED,
        )
        batch = MaintenanceBatch.objects.create(
            section=self.task.asset.section,
            block_window=block_window,
            start_time=block_window.start_time,
            end_time=block_window.end_time,
            status=MaintenanceBatch.Status.SCHEDULED,
        )
        batch.tasks.set([self.task, second_task])

        started = self.client.post(
            f"{self.base_url}/start/",
            {"checklist": [{"item": "PPE", "completed": True}]},
            format="json",
        )
        self.assertEqual(started.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        second_task.refresh_from_db()
        batch.refresh_from_db()
        self.assertEqual(self.task.status, MaintenanceTask.Status.ACTIVE)
        self.assertEqual(second_task.status, MaintenanceTask.Status.ACTIVE)
        self.assertEqual(batch.status, MaintenanceBatch.Status.ACTIVE)

        completed = self.client.post(
            f"{self.base_url}/complete/",
            {"remark": "Shared block work verified"},
            format="json",
        )
        self.assertEqual(completed.status_code, status.HTTP_200_OK)
        second_task.refresh_from_db()
        batch.refresh_from_db()
        self.assertEqual(second_task.status, MaintenanceTask.Status.COMPLETED)
        self.assertEqual(batch.status, MaintenanceBatch.Status.COMPLETED)

    def test_list_returns_created_maintenance_tasks(self):
        response = self.client.get("/railways/maintenance-tasks/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["task_code"], self.task.task_id)

    def test_list_is_paginated_and_newest_first(self):
        newer_task = MaintenanceTask.objects.create(
            task_id="MNT-LIFECYCLE-NEWEST",
            asset=self.task.asset,
            description="Newly logged inspection",
            severity=1,
            priority=MaintenanceTask.Priority.LOW,
            due_date=timezone.localdate() + timedelta(days=2),
            duration_minutes=15,
        )

        response = self.client.get("/railways/maintenance-tasks/?page=1&page_size=1")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertIsNotNone(response.data["next"])
        self.assertEqual(response.data["results"][0]["task_code"], newer_task.task_id)

    def test_list_places_recently_edited_task_first(self):
        newer_task = MaintenanceTask.objects.create(
            task_id="MNT-LIFECYCLE-NEWER",
            asset=self.task.asset,
            description="Newer inspection",
            severity=1,
            priority=MaintenanceTask.Priority.LOW,
            due_date=timezone.localdate() + timedelta(days=2),
            duration_minutes=15,
        )

        response = self.client.patch(
            f"/railways/maintenance-tasks/{self.task.id}/",
            {"details": "Updated inspection scope"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get("/railways/maintenance-tasks/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["task_code"], self.task.task_id)
        self.assertNotEqual(response.data["results"][0]["task_code"], newer_task.task_id)

    def test_overdue_active_task_remains_active_until_user_finishes_it(self):
        self.task.due_date = timezone.localdate() - timedelta(days=1)
        self.task.status = MaintenanceTask.Status.ACTIVE
        # Use queryset update to model active work crossing its original
        # deadline. Listing the queue must not alter user-started work.
        MaintenanceTask.objects.filter(pk=self.task.pk).update(
            due_date=self.task.due_date,
            status=MaintenanceTask.Status.ACTIVE,
        )

        response = self.client.get(f"{self.base_url}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["task_status"], MaintenanceTask.Status.ACTIVE)
        self.assertFalse(response.data["is_delayed"])
