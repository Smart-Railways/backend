from datetime import datetime
from django.utils import timezone
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
    get_block_window_recommendation,
)


class BlockWindowViewSet(ModelViewSet):
    queryset = BlockWindow.objects.select_related("section").all()
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
            section=section,
            maintenance_start=maintenance_start,
            maintenance_end=maintenance_end,
        )

        return Response({
            "has_conflict": conflicts.exists(),
            "conflict_count": conflicts.count(),
            "conflicts": ConflictTrainMovementSerializer(
                conflicts,
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
        service_date = serializer.validated_data["date"]

        task = (
            MaintenanceTask.objects
            .select_related(
                "asset",
                "asset__section",
            )
            .get(task_id=task_id)
        )

        section = task.asset.section

        # Find feasible maintenance windows for the task
        # on the requested date.
        windows = find_feasible_windows(
            section=section,
            service_date=service_date,
            duration_minutes=task.duration_minutes,
            task_id=task.task_id,
        )

        return Response({
            "task_id": task.task_id,
            "date": service_date,
            "section": {
                "id": section.id,
                "name": section.name,
                "source": section.source_station,
                "source_code": section.source_station_code,
                "destination": section.destination_station,
                "destination_code": section.destination_station_code,
            },
            "required_duration_minutes": task.duration_minutes,
            "feasible": bool(windows),
            "windows": FeasibleWindowItemSerializer(
                windows,
                many=True,
            ).data,
        })

    @action(
        detail=True,
        methods=["get"],
        url_path="recommendation",
    )
    def recommendation(self, request, pk=None):
        """
        AI Recommendation: Evaluates an existing block window for train conflicts
        and identifies the optimal alternative slot with zero collisions and
        maximum decision score. Returns a ready-to-use suggested PUT payload.
        """
        block_window = self.get_object()
        task_id = request.query_params.get("task_id")

        rec = get_block_window_recommendation(
            block_window=block_window,
            task_id=task_id,
        )
        return Response(rec)

    @action(
        detail=True,
        methods=["post"],
        url_path="apply-recommendation",
    )
    def apply_recommendation(self, request, pk=None):
        """
        1-Click AI Apply: Automatically updates the block window to the recommended
        optimal slot without requiring manual PUT construction.
        """
        block_window = self.get_object()
        task_id = (
            request.query_params.get("task_id")
            or request.data.get("task_id")
        )

        rec = get_block_window_recommendation(
            block_window=block_window,
            task_id=task_id,
        )

        if not rec.get("recommended_slot"):
            return Response(
                {
                    "error": "No recommended slot available to apply.",
                    "details": rec.get("recommendation_reason"),
                },
                status=400,
            )

        new_slot = rec["recommended_slot"]
        ist = timezone.get_current_timezone()

        block_window.start_time = timezone.make_aware(
            datetime.strptime(
                new_slot["start"],
                "%Y-%m-%d %H:%M:%S",
            ),
            timezone=ist,
        )
        block_window.end_time = timezone.make_aware(
            datetime.strptime(
                new_slot["end"],
                "%Y-%m-%d %H:%M:%S",
            ),
            timezone=ist,
        )
        block_window.save()

        return Response({
            "message": (
                "Block window successfully updated to AI-recommended slot."
            ),
            "recommendation_reason": rec["recommendation_reason"],
            "block_window": BlockWindowSerializer(block_window).data,
        })