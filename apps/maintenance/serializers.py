from rest_framework import serializers

from .models import MaintenanceTask

class MaintenanceTaskSerializer(serializers.ModelSerializer):
    task_code = serializers.CharField(source="task_id")
    details = serializers.CharField(source="description")
    risk_rating = serializers.IntegerField(source="severity")
    urgency = serializers.CharField(source="priority")
    deadline = serializers.DateField(source="due_date")
    estimated_duration = serializers.IntegerField(source="duration_minutes")
    task_status = serializers.CharField(source="status", required=False)
    is_delayed = serializers.BooleanField(source="is_overdue", read_only=True)
    logged_at = serializers.DateTimeField(source="created_at", format="%Y-%m-%d %H:%M:%S", read_only=True)

    asset_name = serializers.CharField(
        source="asset.name",
        read_only=True,
    )
    section_name = serializers.CharField(
        source="asset.section.name",
        read_only=True,
    )

    class Meta:
        model = MaintenanceTask
        fields = [
            "id",
            "task_code",
            "asset",
            "asset_name",
            "section_name",
            "details",
            "risk_rating",
            "urgency",
            "deadline",
            "estimated_duration",
            "task_status",
            "is_delayed",
            "logged_at",
        ]