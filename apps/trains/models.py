from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.corridors.models import RailwaySection

class Train(models.Model):

    class TrainType(models.TextChoices):
        PASSENGER = "PASSENGER", "Passenger"
        EXPRESS = "EXPRESS", "Express"
        RAJDHANI = "RAJDHANI", "Rajdhani"
        VB = "VB", "Vande Bharat"
        SHATABDI = "SHATABDI", "Shatabdi"
        FREIGHT = "FREIGHT", "Freight"

    train_number = models.CharField(
        max_length=10,
        unique=True
    )

    name = models.CharField(
        max_length=100
    )

    train_type = models.CharField(
        max_length=20,
        choices=TrainType.choices
    )

    priority = models.PositiveIntegerField(
        default=5,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(10),
        ]
    )

    def __str__(self):
        return f"{self.train_number} - {self.name}"


class TrainMovement(models.Model):

    train = models.ForeignKey(
        Train,
        on_delete=models.CASCADE,
        related_name="movements"
    )

    section = models.ForeignKey(
        RailwaySection,
        on_delete=models.CASCADE,
        related_name="train_movements"
    )

    entry_time = models.DateTimeField()

    exit_time = models.DateTimeField()

    def __str__(self):
        return f"{self.train} - {self.section}"