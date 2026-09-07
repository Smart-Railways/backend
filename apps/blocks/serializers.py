from rest_framework import serializers

from apps.corridors.models import RailwaySection
from apps.maintenance.models import MaintenanceTask
from apps.trains.models import TrainMovement
from .models import BlockWindow


class BlockWindowSerializer(serializers.ModelSerializer):
    section_name = serializers.CharField(
        source="section.name",
        read_only=True,
    )
    task_code = serializers.CharField(
        source="task.task_id",
        read_only=True,
    )
    task_id = serializers.CharField(
        write_only=True,
        required=False,
        allow_null=True,
    )
    start_time = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S"
    )
    end_time = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S"
    )

    class Meta:
        model = BlockWindow
        fields = [
            "id",
            "section",
            "section_name",
            "task",
            "task_code",
            "task_id",
            "start_time",
            "end_time",
            "status",
        ]

    def create(self, validated_data):
        task_id_str = self.initial_data.get("task_id")
        if task_id_str and not validated_data.get("task"):
            t = MaintenanceTask.objects.filter(task_id=task_id_str).first()
            if t:
                validated_data["task"] = t

        bw = super().create(validated_data)

        # When a block window is created for a maintenance task, automatically mark it SCHEDULED
        if bw.task:
            if bw.task.status != MaintenanceTask.Status.COMPLETED and bw.task.status != MaintenanceTask.Status.CANCELLED:
                bw.task.status = MaintenanceTask.Status.SCHEDULED
                bw.task.save()

        return bw

    def update(self, instance, validated_data):
        task_id_str = self.initial_data.get("task_id")
        if task_id_str and not validated_data.get("task"):
            t = MaintenanceTask.objects.filter(task_id=task_id_str).first()
            if t:
                validated_data["task"] = t

        bw = super().update(instance, validated_data)

        if bw.task:
            if bw.task.status != MaintenanceTask.Status.COMPLETED and bw.task.status != MaintenanceTask.Status.CANCELLED:
                bw.task.status = MaintenanceTask.Status.SCHEDULED
                bw.task.save()

        return bw


class ConflictTrainMovementSerializer(serializers.ModelSerializer):
    train_number = serializers.CharField(
        source="schedule.train.train_number",
        read_only=True,
    )
    train_name = serializers.CharField(
        source="schedule.train.name",
        read_only=True,
    )
    entry_time = serializers.DateTimeField(
        source="actual_entry_time",
        format="%Y-%m-%d %H:%M:%S",
        read_only=True,
    )
    exit_time = serializers.DateTimeField(
        source="actual_exit_time",
        format="%Y-%m-%d %H:%M:%S",
        read_only=True,
    )

    class Meta:
        model = TrainMovement
        fields = [
            "train_number",
            "train_name",
            "entry_time",
            "exit_time",
        ]


class ConflictCheckSerializer(serializers.Serializer):
    section = serializers.PrimaryKeyRelatedField(
        queryset=RailwaySection.objects.all()
    )
    maintenance_start = serializers.DateTimeField()
    maintenance_end = serializers.DateTimeField()

    def validate(self, data):
        if data["maintenance_end"] <= data["maintenance_start"]:
            raise serializers.ValidationError(
                "maintenance_end must be after maintenance_start."
            )

        return data


class FeasibleWindowSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    date = serializers.DateField()

    def validate_task_id(self, value):
        try:
            MaintenanceTask.objects.get(task_id=value)
        except MaintenanceTask.DoesNotExist:
            raise serializers.ValidationError(
                "Maintenance task not found."
            )

        return value


class FeasibleWindowItemSerializer(serializers.Serializer):
    start = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S"
    )
    end = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S"
    )
    duration_minutes = serializers.IntegerField()
    decision_score = serializers.FloatField(
        required=False,
        default=None,
    )
    algorithm = serializers.CharField(
        required=False,
        default=None,
    )