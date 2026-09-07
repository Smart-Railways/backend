from django.utils import timezone
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

    block_window = serializers.SerializerMethodField()
    block_window_date = serializers.SerializerMethodField()

    def get_block_window(self, obj):
        if hasattr(obj, "prefetched_block_windows"):
            bw = obj.prefetched_block_windows[0] if obj.prefetched_block_windows else None
        else:
            bw = obj.block_windows.select_related("section").order_by("-id").first()
        if not bw:
            return None
        start_local = timezone.localtime(bw.start_time) if bw.start_time else None
        end_local = timezone.localtime(bw.end_time) if bw.end_time else None
        duration = None
        if start_local and end_local:
            duration = int((end_local - start_local).total_seconds() // 60)
        return {
            "id": bw.id,
            "section": bw.section_id,
            "section_name": bw.section.name if bw.section else None,
            "date": start_local.strftime("%Y-%m-%d") if start_local else None,
            "start_time": start_local.strftime("%Y-%m-%d %H:%M:%S") if start_local else None,
            "end_time": end_local.strftime("%Y-%m-%d %H:%M:%S") if end_local else None,
            "duration_minutes": duration,
            "status": str(bw.status),
        }

    def get_block_window_date(self, obj):
        if hasattr(obj, "prefetched_block_windows"):
            bw = obj.prefetched_block_windows[0] if obj.prefetched_block_windows else None
        else:
            bw = obj.block_windows.order_by("-id").first()
        if not bw or not bw.start_time:
            return None
        return timezone.localtime(bw.start_time).strftime("%Y-%m-%d")

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
            "block_window",
            "block_window_date",
            "is_delayed",
            "logged_at",
        ]