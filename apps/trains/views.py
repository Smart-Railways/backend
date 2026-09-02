from rest_framework.viewsets import ModelViewSet

from .models import Train, TrainMovement
from .serializers import TrainSerializer, TrainMovementSerializer


class TrainViewSet(ModelViewSet):
    queryset = Train.objects.all()
    serializer_class = TrainSerializer


class TrainMovementViewSet(ModelViewSet):
    queryset = TrainMovement.objects.select_related("train", "section").all()
    serializer_class = TrainMovementSerializer
