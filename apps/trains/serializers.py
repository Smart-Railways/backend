from rest_framework import serializers

from .models import Train, TrainMovement


class TrainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Train
        fields = [
            "id",
            "train_number",
            "name",
            "train_type",
            "priority",
        ]


class TrainMovementSerializer(serializers.ModelSerializer):
    train_number = serializers.CharField(
        source="train.train_number",
        read_only=True,
    )
    train_name = serializers.CharField(
        source="train.name",
        read_only=True,
    )
    section_name = serializers.CharField(
        source="section.name",
        read_only=True,
    )
    entry_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    exit_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")

    class Meta:
        model = TrainMovement
        fields = [
            "id",
            "train",
            "train_number",
            "train_name",
            "section",
            "section_name",
            "entry_time",
            "exit_time",
        ]
