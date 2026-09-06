from django.utils import timezone
from rest_framework.viewsets import ModelViewSet

from .models import MaintenanceTask
from .serializers import MaintenanceTaskSerializer


class MaintenanceTaskViewSet(ModelViewSet):
    serializer_class = MaintenanceTaskSerializer

    def get_queryset(self):
        today = timezone.localdate()

        # Automatically transition expired tasks whose due_date has passed (< today)
        # to DELAYED status and set is_overdue to True
        MaintenanceTask.objects.filter(
            due_date__lt=today,
        ).exclude(
            status__in=[
                MaintenanceTask.Status.COMPLETED,
                MaintenanceTask.Status.CANCELLED,
                MaintenanceTask.Status.DELAYED,
            ]
        ).update(
            status=MaintenanceTask.Status.DELAYED,
            is_overdue=True,
        )

        return (
            MaintenanceTask.objects
            .select_related("asset__section")
            .all()
        )