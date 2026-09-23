from django.db import models

from apps.assets.models import Asset

class MaintenanceTask(models.Model):

    class Priority(models.TextChoices):
        CRITICAL = "CRITICAL", "Critical"
        HIGH = "HIGH", "High"
        MEDIUM = "MEDIUM", "Medium"
        LOW = "LOW", "Low"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SCHEDULED = "SCHEDULED", "Scheduled"
        ACTIVE = "ACTIVE", "Active"
        DELAYED = "DELAYED", "Delayed"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    task_id = models.CharField(
        max_length=100,
        unique=True
    )

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="maintenance_tasks"
    )

    description = models.TextField()

    severity = models.PositiveIntegerField()

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices
    )

    due_date = models.DateField()

    duration_minutes = models.PositiveIntegerField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    is_overdue = models.BooleanField(default=False)

    # Execution evidence submitted through the lifecycle endpoints.  These
    # fields make a completed/cancelled task auditable without requiring a
    # separate maintenance-execution table.
    start_checklist = models.JSONField(default=list, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completion_remark = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancellation_remark = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    # Used by the maintenance queue to surface tasks whose details or linked
    # block window were changed most recently.
    updated_at = models.DateTimeField(auto_now=True)

    def check_and_update_overdue(self):
        """
        If due_date has passed (due_date < today in Asia/Kolkata)
        and status is not COMPLETED or CANCELLED,
        automatically mark status as DELAYED and is_overdue as True.
        """
        from django.utils import timezone
        today = timezone.localdate()
        if (
            self.due_date
            and self.due_date < today
            and self.status not in (self.Status.COMPLETED, self.Status.CANCELLED)
        ):
            # A task is transitioned to DELAYED only once.  If a controller
            # later assigns it a recovery block window, SCHEDULED must remain
            # available so the team can start that recovery work; is_overdue
            # keeps the missed deadline visible.
            was_overdue = self.is_overdue
            self.is_overdue = True
            if not was_overdue:
                self.status = self.Status.DELAYED
                return True
        return False

    def save(self, *args, **kwargs):
        self.check_and_update_overdue()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.task_id


class MaintenanceLog(models.Model):
    """Append-only audit record for maintenance operations."""

    class Event(models.TextChoices):
        CREATED = "CREATED", "Created"
        UPDATED = "UPDATED", "Updated"
        SCHEDULED = "SCHEDULED", "Scheduled"
        STARTED = "STARTED", "Started"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        DELAYED = "DELAYED", "Delayed"
        DELETED = "DELETED", "Deleted"

    task = models.ForeignKey(
        MaintenanceTask,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs",
    )
    # This snapshot keeps a deleted task's audit trail searchable.
    task_code = models.CharField(max_length=100, db_index=True)
    event = models.CharField(max_length=20, choices=Event.choices)
    status = models.CharField(max_length=20, choices=MaintenanceTask.Status.choices)
    remark = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.task_code} | {self.event}"
