from django.db import models
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    RegexValidator,
)

from apps.corridors.models import RailwaySection


class Train(models.Model):

    class TrainType(models.TextChoices):
        PASSENGER = "PASSENGER", "Passenger"
        EXPRESS = "EXPRESS", "Express"
        RAJDHANI = "RAJDHANI", "Rajdhani"
        VB = "VB", "Vande Bharat"
        SHATABDI = "SHATABDI", "Shatabdi"
        FREIGHT = "FREIGHT", "Freight"

    train_number = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)

    train_type = models.CharField(
        max_length=20,
        choices=TrainType.choices,
    )

    priority = models.PositiveIntegerField(
        default=5,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(10),
        ],
    )

    def __str__(self):
        return f"{self.train_number} - {self.name}"


class TrainSchedule(models.Model):

    running_days_validator = RegexValidator(
        regex=r"^[01]{7}$",
        message="running_days must contain exactly 7 characters of 0 or 1.",
    )

    train = models.ForeignKey(
        Train,
        on_delete=models.CASCADE,
        related_name="schedules",
    )

    section = models.ForeignKey(
        RailwaySection,
        on_delete=models.CASCADE,
        related_name="train_schedules",
    )

    scheduled_entry_time = models.TimeField()

    scheduled_exit_time = models.TimeField()

    # 0 = exit on the same day
    # 1 = exit on the next day
    scheduled_exit_day_offset = models.PositiveSmallIntegerField(
        default=0,
    )

    # Monday → Sunday
    # 1111111 = every day
    # 1111100 = Monday-Friday
    # 0000011 = Saturday-Sunday
    running_days = models.CharField(
        max_length=7,
        default="1111111",
        validators=[running_days_validator],
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return (
            f"{self.train} | "
            f"{self.section} | "
            f"{self.scheduled_entry_time} - "
            f"{self.scheduled_exit_time}"
        )


class TrainMovement(models.Model):

    schedule = models.ForeignKey(
        TrainSchedule,
        on_delete=models.CASCADE,
        related_name="movements",
    )

    service_date = models.DateField()

    # Actual times received from live train API
    actual_entry_time = models.DateTimeField(
        null=True,
        blank=True,
    )

    actual_exit_time = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["schedule", "service_date"],
                name="unique_train_movement_per_day",
            )
        ]

        indexes = [
            models.Index(
                fields=["schedule", "service_date"],
            )
        ]

    def __str__(self):
        return f"{self.schedule.train} - {self.service_date}"