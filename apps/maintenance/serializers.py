from django.utils import timezone
from rest_framework import serializers

from .models import MaintenanceLog, MaintenanceTask


class StartMaintenanceSerializer(serializers.Serializer):
    """Validates the checklist submitted before work can begin."""

    checklist = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
        write_only=True,
    )

    def validate_checklist(self, value):
        for index, entry in enumerate(value):
            item = str(entry.get("item", "")).strip()
            # `completed` is the API contract; `checked` is accepted for the
            # existing form convention used by some clients.
            completed = entry.get("completed", entry.get("checked"))
            if not item:
                raise serializers.ValidationError(
                    f"Checklist item {index + 1} must include a non-empty 'item'."
                )
            if completed is not True:
                raise serializers.ValidationError(
                    "Every checklist item must be completed before maintenance can start."
                )
        return value


class MaintenanceRemarkSerializer(serializers.Serializer):
    remark = serializers.CharField(trim_whitespace=True, allow_blank=False)


class MaintenanceLogSerializer(serializers.ModelSerializer):
    task_id = serializers.IntegerField(read_only=True)
    logged_at = serializers.DateTimeField(source="created_at", format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = MaintenanceLog
        fields = [
            "id",
            "task_id",
            "task_code",
            "event",
            "status",
            "remark",
            "details",
            "logged_at",
        ]

class MaintenanceTaskSerializer(serializers.ModelSerializer):
    task_code = serializers.CharField(source="task_id")
    details = serializers.CharField(source="description")
    risk_rating = serializers.IntegerField(source="severity")
    urgency = serializers.CharField(source="priority")
    deadline = serializers.DateField(source="due_date")
    estimated_duration = serializers.IntegerField(source="duration_minutes")
    task_status = serializers.ChoiceField(
        source="status",
        choices=MaintenanceTask.Status.choices,
        required=False,
    )
    is_delayed = serializers.BooleanField(source="is_overdue", read_only=True)
    logged_at = serializers.DateTimeField(source="created_at", format="%Y-%m-%d %H:%M:%S", read_only=True)
    checklist = serializers.JSONField(source="start_checklist", read_only=True)
    started_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    completion_remark = serializers.CharField(read_only=True)
    completed_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    cancellation_remark = serializers.CharField(read_only=True)
    cancelled_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

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
            "checklist",
            "started_at",
            "completion_remark",
            "completed_at",
            "cancellation_remark",
            "cancelled_at",
            "logged_at",
        ]

    def validate_task_status(self, value):
        """Lifecycle-only statuses cannot be assigned through generic CRUD."""
        protected = {
            MaintenanceTask.Status.ACTIVE,
            MaintenanceTask.Status.COMPLETED,
            MaintenanceTask.Status.CANCELLED,
        }
        if value in protected:
            raise serializers.ValidationError(
                "Use the start, complete, or cancel maintenance endpoint for this status."
            )
        return value
