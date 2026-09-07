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

    def _handle_recommendation(self, request, block_window=None):
        """
        Unified AI Recommendation & Rescheduling Handler.
        Merges slot discovery, conflict recommendation, and auto-apply into ONE workflow:
        1. Pre-creation discovery: { task_id, date } -> Returns optimal conflict-free slots.
        2. Post-creation monitoring: { block_window_id, task_id } -> Returns conflicts & AI slot.
        3. Auto-apply: { block_window_id, apply: true } -> Updates block window to AI slot in DB.
        """
        data = request.data if request.method == "POST" else request.query_params

        # 1. Resolve block window ID
        block_window_id = (
            (block_window.id if block_window else None)
            or data.get("block_window_id")
            or data.get("block_id")
        )

        target_bw = block_window
        if not target_bw and block_window_id:
            try:
                target_bw = BlockWindow.objects.select_related("section").get(id=block_window_id)
            except BlockWindow.DoesNotExist:
                return Response(
                    {"error": f"BlockWindow #{block_window_id} not found."},
                    status=404,
                )

        # 2. Extract parameters
        task_id = data.get("task_id")
        date_param = data.get("date")
        apply_flag = str(data.get("apply", "")).lower() in ("true", "1", "yes")

        # 3. Handle when BlockWindow is present (Monitoring / Rescheduling / Auto-apply)
        if target_bw:
            rec = get_block_window_recommendation(
                block_window=target_bw,
                task_id=task_id,
            )

            if apply_flag:
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

                target_bw.start_time = timezone.make_aware(
                    datetime.strptime(
                        new_slot["start"],
                        "%Y-%m-%d %H:%M:%S",
                    ),
                    timezone=ist,
                )
                target_bw.end_time = timezone.make_aware(
                    datetime.strptime(
                        new_slot["end"],
                        "%Y-%m-%d %H:%M:%S",
                    ),
                    timezone=ist,
                )
                target_bw.save()

                if task_id:
                    MaintenanceTask.objects.filter(task_id=task_id).update(
                        status=MaintenanceTask.Status.SCHEDULED
                    )

                return Response({
                    "applied": True,
                    "message": (
                        "Block window successfully updated to AI-recommended slot."
                    ),
                    "recommendation_reason": rec["recommendation_reason"],
                    "block_window": BlockWindowSerializer(target_bw).data,
                    "recommended_slot": rec["recommended_slot"],
                })

            return Response(rec)

        # 4. Handle when BlockWindow is NOT yet created (Pre-creation discovery)
        if not task_id:
            return Response(
                {
                    "error": (
                        "Either 'block_window_id' or 'task_id' must be provided."
                    )
                },
                status=400,
            )

        task = (
            MaintenanceTask.objects
            .select_related("asset", "asset__section")
            .filter(task_id=task_id)
            .first()
        )
        if not task:
            return Response(
                {"error": f"Maintenance task '{task_id}' not found."},
                status=404,
            )

        section = task.asset.section

        # Resolve planning date
        if date_param:
            try:
                service_date = (
                    datetime.strptime(str(date_param)[:10], "%Y-%m-%d").date()
                )
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD."},
                    status=400,
                )
        elif task.due_date:
            service_date = task.due_date
        else:
            service_date = timezone.localdate()

        windows = find_feasible_windows(
            section=section,
            service_date=service_date,
            duration_minutes=task.duration_minutes,
            task_id=task.task_id,
        )

        best_slot = None
        if windows:
            sorted_w = sorted(
                windows,
                key=lambda x: x.get("decision_score") or 0.0,
                reverse=True,
            )
            best = sorted_w[0]
            score_val = best.get("decision_score")
            best_slot = {
                "start": best["start"].strftime("%Y-%m-%d %H:%M:%S"),
                "end": best["end"].strftime("%Y-%m-%d %H:%M:%S"),
                "duration_minutes": best["duration_minutes"],
                "decision_score": (
                    round(score_val, 3) if score_val is not None else None
                ),
                "algorithm": best.get("algorithm"),
            }

        # If user passed apply=true even without block_window_id, auto-create the BlockWindow!
        if apply_flag:
            if not best_slot:
                return Response(
                    {"error": "No conflict-free slots found to auto-schedule."},
                    status=400,
                )

            ist = timezone.get_current_timezone()
            new_bw = BlockWindow.objects.create(
                section=section,
                start_time=timezone.make_aware(
                    datetime.strptime(best_slot["start"], "%Y-%m-%d %H:%M:%S"),
                    timezone=ist,
                ),
                end_time=timezone.make_aware(
                    datetime.strptime(best_slot["end"], "%Y-%m-%d %H:%M:%S"),
                    timezone=ist,
                ),
                status=BlockWindow.Status.RESERVED,
            )
            task.status = MaintenanceTask.Status.SCHEDULED
            task.save()

            return Response({
                "applied": True,
                "message": "Block window created and assigned to AI-recommended slot.",
                "recommendation_reason": (
                    f"AI allocated collision-free slot with score {best_slot.get('decision_score')}."
                ),
                "block_window": BlockWindowSerializer(new_bw).data,
                "recommended_slot": best_slot,
            })

        return Response({
            "task_id": task.task_id,
            "date": str(service_date),
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
            "has_better_slot": bool(best_slot),
            "recommendation_reason": (
                f"AI identified {len(windows)} conflict-free slot(s) for task {task.task_id}. Optimal slot is {best_slot['start']} - {best_slot['end']}."
                if best_slot else "No feasible maintenance windows found for this corridor on target date."
            ),
            "recommended_slot": best_slot,
            "suggested_put_payload": {
                "section": section.id,
                "start_time": best_slot["start"],
                "end_time": best_slot["end"],
                "status": "RESERVED",
            } if best_slot else None,
            "windows": FeasibleWindowItemSerializer(windows, many=True).data,
        })

    @action(
        detail=False,
        methods=["get", "post"],
        url_path="recommendation",
    )
    def unified_recommendation(self, request):
        """
        Unified AI Recommendation Endpoint:
        Merges slot discovery, conflict recommendation, and auto-apply into ONE endpoint.
        - Discover feasible slots before creation: POST/GET with { task_id, date }
        - Check AI recommendation & conflicts: POST/GET with { block_window_id, task_id }
        - Auto-apply AI recommendation: POST with { block_window_id, apply: true }
        """
        return self._handle_recommendation(request)

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="recommendation",
    )
    def detail_recommendation(self, request, pk=None):
        block_window = self.get_object()
        return self._handle_recommendation(request, block_window=block_window)

    @action(
        detail=False,
        methods=["post"],
        url_path="feasible-windows",
    )
    def feasible_windows(self, request):
        """Backward compatibility alias for feasible-windows"""
        return self._handle_recommendation(request)

    @action(
        detail=True,
        methods=["post"],
        url_path="apply-recommendation",
    )
    def apply_recommendation(self, request, pk=None):
        """Backward compatibility alias for apply-recommendation"""
        block_window = self.get_object()
        return self._handle_recommendation(request, block_window=block_window)