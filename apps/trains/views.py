from rest_framework import viewsets

from .models import Train, TrainSchedule, TrainMovement
from .serializers import (
    TrainSerializer,
    TrainScheduleSerializer,
    TrainMovementSerializer,
)


class TrainViewSet(viewsets.ModelViewSet):
    queryset = Train.objects.all()
    serializer_class = TrainSerializer


class TrainScheduleViewSet(viewsets.ModelViewSet):
    queryset = TrainSchedule.objects.select_related(
        "train",
        "section"
    ).all()

    serializer_class = TrainScheduleSerializer


class TrainMovementViewSet(viewsets.ModelViewSet):
    queryset = TrainMovement.objects.select_related(
        "schedule",
        "schedule__train",
        "schedule__section",
    ).all()

    serializer_class = TrainMovementSerializer