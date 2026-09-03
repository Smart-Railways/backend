from django.db import models

class RailwaySection(models.Model):
    name = models.CharField(max_length=200)

    source_station = models.CharField(max_length=100)
    source_station_code = models.CharField(max_length=10)

    destination_station = models.CharField(max_length=100)
    destination_station_code = models.CharField(max_length=10)

    distance_km = models.FloatField()

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name