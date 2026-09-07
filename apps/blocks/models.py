from django.db import models

from apps.corridors.models import RailwaySection

class BlockWindow(models.Model):

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        RESERVED = "RESERVED", "Reserved"
        BLOCKED = "BLOCKED", "Blocked"

    section = models.ForeignKey(
        RailwaySection,
        on_delete=models.CASCADE,
        related_name="block_windows"
    )

    task = models.ForeignKey(
        "maintenance.MaintenanceTask",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="block_windows"
    )

    start_time = models.DateTimeField()

    end_time = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE
    )

    def __str__(self):
        return f"{self.section} | {self.start_time} - {self.end_time}"