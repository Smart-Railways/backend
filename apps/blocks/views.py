from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from apps.maintenance.models import MaintenanceTask

from .models import BlockWindow
from .serializers import (
    BlockWindowSerializer,
    ConflictCheckSerializer,
    ConflictTrainMovementSerializer,
    FeasibleWindowSerializer,
    FeasibleWindowItemSerializer,
)
from .services import (
    find_feasible_windows,
    find_train_conflicts,
)


class BlockWindowViewSet(ModelViewSet):
    queryset = BlockWindow.objects.all()
    serializer_class = BlockWindowSerializer

    @action(
        detail=False,
        methods=["post"],
        url_path="check-conflict",
    )
    def check_conflict(self, request):
        serializer = ConflictCheckSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        section = serializer.validated_data["section"]
        maintenance_start = serializer.validated_data[
            "maintenance_start"
        ]
        maintenance_end = serializer.validated_data[
            "maintenance_end"
        ]

        conflicts = find_train_conflicts(
            section,
            maintenance_start,
            maintenance_end,
        )

        return Response({
            "has_conflict": conflicts.exists(),
            "conflict_count": conflicts.count(),
            "conflicts": ConflictTrainMovementSerializer(
                conflicts.select_related("train"),
                many=True,
            ).data,
        })

    @action(
        detail=False,
        methods=["post"],
        url_path="feasible-windows",
    )
    def feasible_windows(self, request):
        serializer = FeasibleWindowSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        task_id = serializer.validated_data["task_id"]
        block = serializer.validated_data["block_id"]

        task = MaintenanceTask.objects.get(
            task_id=task_id
        )

        # Make sure task and block belong to same section
        if task.asset.section_id != block.section_id:
            return Response(
                {
                    "error": (
                        "Maintenance task and block "
                        "belong to different sections."
                    )
                },
                status=400,
            )

        windows = find_feasible_windows(
            section=block.section,
            block_start=block.start_time,
            block_end=block.end_time,
            duration_minutes=task.duration_minutes,
        )

        return Response({
            "task_id": task.task_id,
            "block_id": block.id,
            "section": block.section.name,
            "required_duration_minutes": task.duration_minutes,
            "feasible": len(windows) > 0,
            "windows": FeasibleWindowItemSerializer(
                windows,
                many=True,
            ).data,
        })