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

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def check_and_update_overdue(self):
        """
        If due_date has passed (due_date < today in Asia/Kolkata)
        and status is not COMPLETED or CANCELLED,
        automatically mark status as DELAYED and is_overdue as True.
        """
        from django.utils import timezone
        today = timezone.localdate()
        if self.due_date and self.due_date < today:
            if self.status not in (self.Status.COMPLETED, self.Status.CANCELLED):
                self.status = self.Status.DELAYED
                self.is_overdue = True
                return True
        return False

    def save(self, *args, **kwargs):
        self.check_and_update_overdue()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.task_id