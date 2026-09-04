from rest_framework import serializers

from .models import Train, TrainSchedule, TrainMovement


class TrainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Train
        fields = "__all__"


class TrainScheduleSerializer(serializers.ModelSerializer):
    train_name = serializers.CharField(
        source="train.name",
        read_only=True
    )

    section_name = serializers.CharField(
        source="section.name",
        read_only=True
    )

    class Meta:
        model = TrainSchedule
        fields = [
            "id",
            "train",
            "train_name",
            "section",
            "section_name",
            "scheduled_entry_time",
            "scheduled_exit_time",
            "running_days",
            "is_active",
        ]

    def validate(self, data):
        if data["scheduled_exit_time"] <= data["scheduled_entry_time"]:
            raise serializers.ValidationError(
                "scheduled_exit_time must be after scheduled_entry_time."
            )

        return data


class TrainMovementSerializer(serializers.ModelSerializer):
    train = serializers.CharField(
        source="schedule.train.name",
        read_only=True
    )

    train_number = serializers.CharField(
        source="schedule.train.train_number",
        read_only=True
    )

    section = serializers.CharField(
        source="schedule.section.name",
        read_only=True
    )

    scheduled_entry_time = serializers.TimeField(
        source="schedule.scheduled_entry_time",
        read_only=True
    )

    scheduled_exit_time = serializers.TimeField(
        source="schedule.scheduled_exit_time",
        read_only=True
    )

    class Meta:
        model = TrainMovement
        fields = [
            "id",
            "schedule",
            "service_date",
            "actual_entry_time",
            "actual_exit_time",
            "train",
            "train_number",
            "section",
            "scheduled_entry_time",
            "scheduled_exit_time",
        ]

    def validate(self, data):
        actual_entry = data.get("actual_entry_time")
        actual_exit = data.get("actual_exit_time")

        if actual_entry and actual_exit and actual_exit <= actual_entry:
            raise serializers.ValidationError(
                "actual_exit_time must be after actual_entry_time."
            )

        return data

class TrainOperationsSerializer(serializers.Serializer):
    train_number = serializers.CharField()
    train_name = serializers.CharField()
    train_type = serializers.CharField()
    priority = serializers.IntegerField()

    section = serializers.DictField()

    schedule = serializers.DictField()

    movement = serializers.DictField(allow_null=True)

    delay_minutes = serializers.IntegerField(allow_null=True)