from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.blocks.models import BlockWindow
from .models import MaintenanceBatch, MaintenanceLog, MaintenanceTask
from .pagination import MaintenanceTaskPagination
from .serializers import (
    MaintenanceLogSerializer,
    MaintenanceBatchSerializer,
    MaintenanceRemarkSerializer,
    MaintenanceTaskSerializer,
    StartMaintenanceSerializer,
)


class MaintenanceTaskViewSet(ModelViewSet):
    serializer_class = MaintenanceTaskSerializer
    pagination_class = MaintenanceTaskPagination

    def get_queryset(self):
        today = timezone.localdate()

        # Automatically transition expired non-active tasks whose due_date has
        # passed (< today) to DELAYED. Active maintenance is controlled only by
        # the explicit complete/cancel lifecycle actions.
        overdue_tasks = MaintenanceTask.objects.filter(
            due_date__lt=today,
            is_overdue=False,
        ).exclude(
            status__in=[
                MaintenanceTask.Status.COMPLETED,
                MaintenanceTask.Status.CANCELLED,
                MaintenanceTask.Status.DELAYED,
                MaintenanceTask.Status.ACTIVE,
            ]
        )
        # Iterate so an automatic delay is auditable, rather than using a
        # bulk update that bypasses the audit table.
        for overdue_task in overdue_tasks:
            overdue_task.status = MaintenanceTask.Status.DELAYED
            overdue_task.is_overdue = True
            overdue_task.save()
            self._log(overdue_task, MaintenanceLog.Event.DELAYED)

        return (
            MaintenanceTask.objects
            .select_related("asset__section", "shared_block_window__section")
            .prefetch_related(
                Prefetch(
                    "block_windows",
                    queryset=BlockWindow.objects.select_related("section").order_by("-id"),
                    to_attr="prefetched_block_windows",
                )
            )
            # Surface newly created and recently edited tasks first. A linked
            # block-window edit also saves its task, refreshing updated_at.
            .order_by("-updated_at", "-id")
            .all()
        )

    @staticmethod
    def _log(task, event, remark="", details=None):
        MaintenanceLog.objects.create(
            task=task,
            task_code=task.task_id,
            event=event,
            status=task.status,
            remark=remark,
            details=details or {},
        )

    @staticmethod
    def _active_batch_for_task(task):
        """Return the current shared batch, if this task is part of one."""
        return (
            task.maintenance_batches.exclude(
                status__in=[
                    MaintenanceBatch.Status.COMPLETED,
                    MaintenanceBatch.Status.CANCELLED,
                ]
            )
            .order_by("-id")
            .first()
        )

    def _start_batch(self, batch, checklist):
        batch_tasks = list(batch.tasks.all())
        if any(task.status != MaintenanceTask.Status.SCHEDULED for task in batch_tasks):
            return None

        started_at = timezone.now()
        for batch_task in batch_tasks:
            batch_task.start_checklist = checklist
            batch_task.started_at = started_at
            batch_task.status = MaintenanceTask.Status.ACTIVE
            batch_task.save()
            self._log(
                batch_task,
                MaintenanceLog.Event.STARTED,
                details={"checklist": checklist, "maintenance_batch_id": batch.id},
            )
        batch.status = MaintenanceBatch.Status.ACTIVE
        batch.save(update_fields=["status", "updated_at"])
        return batch_tasks

    def _finish_batch(self, batch, status_value, event, remark):
        batch_tasks = list(batch.tasks.all())
        finished_at = timezone.now()
        for batch_task in batch_tasks:
            if status_value == MaintenanceTask.Status.COMPLETED:
                batch_task.completion_remark = remark
                batch_task.completed_at = finished_at
            else:
                batch_task.cancellation_remark = remark
                batch_task.cancelled_at = finished_at
            batch_task.status = status_value
            batch_task.save()
            self._log(
                batch_task,
                event,
                remark,
                details={"maintenance_batch_id": batch.id},
            )
        batch.status = (
            MaintenanceBatch.Status.COMPLETED
            if status_value == MaintenanceTask.Status.COMPLETED
            else MaintenanceBatch.Status.CANCELLED
        )
        batch.save(update_fields=["status", "updated_at"])
        return batch_tasks

    def perform_create(self, serializer):
        task = serializer.save()
        self._log(task, MaintenanceLog.Event.CREATED)

    def perform_update(self, serializer):
        task = serializer.save()
        self._log(task, MaintenanceLog.Event.UPDATED)

    def perform_destroy(self, instance):
        instance.delete()

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        """Start a scheduled task only after its full checklist is submitted."""
        task = self.get_object()
        payload = StartMaintenanceSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        if task.status != MaintenanceTask.Status.SCHEDULED:
            return Response(
                {"detail": "Only a SCHEDULED maintenance task can be started."},
                status=status.HTTP_409_CONFLICT,
            )

        batch = self._active_batch_for_task(task)
        with transaction.atomic():
            if batch:
                if not self._start_batch(batch, payload.validated_data["checklist"]):
                    return Response(
                        {"detail": "Every task in the shared batch must be SCHEDULED before it can start."},
                        status=status.HTTP_409_CONFLICT,
                    )
            else:
                task.start_checklist = payload.validated_data["checklist"]
                task.started_at = timezone.now()
                task.status = MaintenanceTask.Status.ACTIVE
                task.save()
                self._log(
                    task,
                    MaintenanceLog.Event.STARTED,
                    details={"checklist": task.start_checklist},
                )

        task.refresh_from_db()
        return Response(self.get_serializer(task).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Complete active work after recording the required completion remark."""
        task = self.get_object()
        payload = MaintenanceRemarkSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        if (
            task.status not in (MaintenanceTask.Status.ACTIVE, MaintenanceTask.Status.DELAYED)
            or not task.started_at
        ):
            return Response(
                {"detail": "Only started ACTIVE or DELAYED maintenance can be completed."},
                status=status.HTTP_409_CONFLICT,
            )

        batch = self._active_batch_for_task(task)
        with transaction.atomic():
            if batch:
                self._finish_batch(
                    batch,
                    MaintenanceTask.Status.COMPLETED,
                    MaintenanceLog.Event.COMPLETED,
                    payload.validated_data["remark"],
                )
            else:
                task.completion_remark = payload.validated_data["remark"]
                task.completed_at = timezone.now()
                task.status = MaintenanceTask.Status.COMPLETED
                task.save()
                self._log(task, MaintenanceLog.Event.COMPLETED, task.completion_remark)
        task.refresh_from_db()
        return Response(self.get_serializer(task).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel non-terminal work after recording the required reason."""
        task = self.get_object()
        payload = MaintenanceRemarkSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        if task.status in (MaintenanceTask.Status.COMPLETED, MaintenanceTask.Status.CANCELLED):
            return Response(
                {"detail": "Completed or cancelled maintenance cannot be cancelled."},
                status=status.HTTP_409_CONFLICT,
            )

        batch = self._active_batch_for_task(task)
        with transaction.atomic():
            if batch:
                self._finish_batch(
                    batch,
                    MaintenanceTask.Status.CANCELLED,
                    MaintenanceLog.Event.CANCELLED,
                    payload.validated_data["remark"],
                )
            else:
                task.cancellation_remark = payload.validated_data["remark"]
                task.cancelled_at = timezone.now()
                task.status = MaintenanceTask.Status.CANCELLED
                task.save()
                self._log(task, MaintenanceLog.Event.CANCELLED, task.cancellation_remark)
        task.refresh_from_db()
        return Response(self.get_serializer(task).data, status=status.HTTP_200_OK)


class MaintenanceLogViewSet(ReadOnlyModelViewSet):
    """Read-only maintenance audit trail; records are written by task actions."""

    serializer_class = MaintenanceLogSerializer

    def get_queryset(self):
        queryset = MaintenanceLog.objects.select_related("task").all()
        task_id = self.request.query_params.get("task_id")
        task_code = self.request.query_params.get("task_code")
        event = self.request.query_params.get("event")
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        if task_code:
            queryset = queryset.filter(task_code__iexact=task_code)
        if event:
            queryset = queryset.filter(event=event.upper())
        return queryset


class MaintenanceBatchViewSet(ReadOnlyModelViewSet):
    """Read a shared maintenance block and every task assigned to it."""

    serializer_class = MaintenanceBatchSerializer

    def get_queryset(self):
        return (
            MaintenanceBatch.objects.select_related("section", "block_window")
            .prefetch_related(
                Prefetch(
                    "tasks",
                    queryset=MaintenanceTask.objects.select_related("asset").order_by("due_date", "id"),
                    to_attr="prefetched_tasks",
                )
            )
            .order_by("-start_time", "-id")
        )
