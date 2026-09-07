from django.db.models import Prefetch
from django.utils import timezone
from rest_framework.viewsets import ModelViewSet

from apps.blocks.models import BlockWindow
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
            .prefetch_related(
                Prefetch(
                    "block_windows",
                    queryset=BlockWindow.objects.select_related("section").order_by("-id"),
                    to_attr="prefetched_block_windows",
                )
            )
            .all()
        )