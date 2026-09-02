from rest_framework import serializers

from .models import BlockWindow


class BlockWindowSerializer(serializers.ModelSerializer):
    section_name = serializers.CharField(
        source="section.name",
        read_only=True,
    )
    start_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    end_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")

    class Meta:
        model = BlockWindow
        fields = [
            "id",
            "section",
            "section_name",
            "start_time",
            "end_time",
            "status",
        ]
