from rest_framework.viewsets import ModelViewSet

from .models import MaintenanceTask
from .serializers import MaintenanceTaskSerializer

class MaintenanceTaskViewSet(ModelViewSet):
    queryset = MaintenanceTask.objects.select_related("asset__section").all()
    serializer_class = MaintenanceTaskSerializer