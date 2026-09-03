from rest_framework import serializers

from .models import RailwaySection


class RailwaySectionSerializer(serializers.ModelSerializer):
    section_name = serializers.CharField(source="name")
    origin_station = serializers.CharField(source="source_station")
    end_station = serializers.CharField(source="destination_station")
    distance = serializers.FloatField(source="distance_km")
    status = serializers.BooleanField(source="is_active", default=True)

    class Meta:
        model = RailwaySection
        fields = [
            "id",
            "section_name",
            "origin_station",
            "source_station_code",
            "end_station",
            "destination_station_code",
            "distance",
            "status",
        ]