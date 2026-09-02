from django.db import models
from apps.trains.models import RailwaySection

class Asset(models.Model):

    class Department(models.TextChoices):
        ENGINEERING = "ENGINEERING", "Engineering"
        SNT = "SNT", "Signal & Telecom"
        TRACTION = "TRACTION", "Traction"

    section = models.ForeignKey(
        RailwaySection,
        on_delete=models.CASCADE,
        related_name="assets"
    )

    name = models.CharField(max_length=200)

    asset_type = models.CharField(max_length=100)

    department = models.CharField(
        max_length=20,
        choices=Department.choices
    )

    criticality = models.PositiveIntegerField()

    installation_date = models.DateField(
        null=True,
        blank=True
    )

    def __str__(self):
        return self.name