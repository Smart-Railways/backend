from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.maintenance.models import MaintenanceBatch, MaintenanceLog, MaintenanceTask
from config.throttling import AIEndpointThrottle

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
    find_next_feasible_windows,
    find_train_conflicts,
    get_block_window_recommendation,
)


class BlockWindowViewSet(ModelViewSet):
    serializer_class = BlockWindowSerializer

    def get_queryset(self):
        qs = BlockWindow.objects.select_related("section", "task", "task__asset").all().order_by("id")
        task_id = self.request.query_params.get("task_id")
        task_pk = self.request.query_params.get("task")
        if task_id:
            qs = qs.filter(task__task_id=task_id)
        elif task_pk:
            qs = qs.filter(task_id=task_pk)
        return qs

    @action(
        detail=False,
        methods=["get", "put", "patch", "delete"],
        url_path=r"by-task/(?P<task_id>[\w-]+)",
    )
    def by_task(self, request, task_id=None):
        """
        Retrieve, update, or delete the Block Window for a specific maintenance task ID.
        GET/PUT/PATCH/DELETE /railways/block-windows/by-task/{task_id}/
        """
        task = MaintenanceTask.objects.filter(task_id=task_id).first()
        if not task:
            return Response(
                {"error": f"Maintenance task '{task_id}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        bw = (
            BlockWindow.objects
            .select_related("section", "task", "task__asset")
            .filter(task=task)
            .order_by("-id")
            .first()
        )

        if request.method == "GET":
            if not bw:
                return Response(
                    {"error": f"No block window found for task '{task_id}'."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(self.get_serializer(bw).data)

        elif request.method == "DELETE":
            if not bw:
                return Response(
                    {"error": f"No block window found for task '{task_id}'."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            bw.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        elif request.method in ["PUT", "PATCH"]:
            partial = request.method == "PATCH" or "section" not in request.data
            if not bw:
                data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
                if "section" not in data and task.asset and task.asset.section_id:
                    data["section"] = task.asset.section_id
                data["task"] = task.id
                data["task_id"] = task.task_id
                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            serializer = self.get_serializer(bw, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        url_path="check-conflict",
        throttle_classes=[AIEndpointThrottle],
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
        url_path="combined-recommendation",
        throttle_classes=[AIEndpointThrottle],
    )
    def combined_recommendation(self, request):
        """Recommend or create one shared block for nearby scheduled blocks."""
        task_id = request.data.get("task_id")
        try:
            nearby_days = int(request.data.get("nearby_days", 2))
        except (TypeError, ValueError):
            return Response({"error": "nearby_days must be an integer."}, status=400)
        if not task_id or nearby_days < 0 or nearby_days > 30:
            return Response(
                {"error": "task_id is required and nearby_days must be between 0 and 30."},
                status=400,
            )

        anchor = (
            MaintenanceTask.objects.select_related("asset__section")
            .filter(task_id=task_id)
            .first()
        )
        if not anchor:
            return Response({"error": f"Maintenance task '{task_id}' not found."}, status=404)
        if anchor.status in (
            MaintenanceTask.Status.ACTIVE,
            MaintenanceTask.Status.COMPLETED,
            MaintenanceTask.Status.CANCELLED,
        ):
            return Response(
                {"error": "Only pending, scheduled, or delayed tasks can be combined."},
                status=status.HTTP_409_CONFLICT,
            )
        apply = str(request.data.get("apply", "")).lower() in ("true", "1", "yes")

        # Combined maintenance is driven by the work's *scheduled block*, not
        # by its maintenance deadline.  This lets tasks with unrelated due
        # dates share one possession when their existing blocks are close on
        # the same corridor.
        anchor_window = (
            BlockWindow.objects.select_related("section")
            .filter(
                task=anchor,
                status__in=(BlockWindow.Status.RESERVED, BlockWindow.Status.BLOCKED),
            )
            .order_by("-start_time", "-id")
            .first()
        )
        if not anchor_window:
            return Response({
                "combined_eligible": False,
                "reason_code": "NO_SCHEDULED_BLOCK_WINDOW",
                "message": "The selected task needs a reserved or blocked schedule window before it can be combined.",
                "nearby_days": nearby_days,
                "minimum_task_count": 2,
                "task_count": 1,
                "tasks": [],
                "recommended_slot": None,
                "applied": False,
                "batch_id": None,
                "block_window": None,
            }, status=status.HTTP_409_CONFLICT if apply else status.HTTP_200_OK)

        section = anchor_window.section
        planning_date = timezone.localtime(anchor_window.start_time).date()
        start_date = planning_date - timedelta(days=nearby_days)
        end_date = planning_date + timedelta(days=nearby_days)
        scheduled_windows = (
            BlockWindow.objects.select_related("task__asset")
            .filter(
                section=section,
                status__in=(BlockWindow.Status.RESERVED, BlockWindow.Status.BLOCKED),
                start_time__date__range=(start_date, end_date),
                task__isnull=False,
            )
            .exclude(task__status__in=[
                MaintenanceTask.Status.ACTIVE,
                MaintenanceTask.Status.COMPLETED,
                MaintenanceTask.Status.CANCELLED,
            ])
            .order_by("start_time", "id")
        )
        # Multiple scheduled windows may point to a task.  Combine distinct
        # assets only; no task deadline is consulted in this selection.
        candidates_by_asset = {anchor.asset_id: anchor}
        for window in scheduled_windows:
            task = window.task
            if task.asset_id != anchor.asset_id:
                candidates_by_asset.setdefault(task.asset_id, task)
        candidates = list(candidates_by_asset.values())

        if len(candidates) < 2:
            payload = {
                "combined_eligible": False,
                "reason_code": "NO_NEARBY_COMPATIBLE_TASKS",
                "message": (
                    "No scheduled block for a different asset was found on "
                    f"this corridor within {nearby_days} day(s) of the anchor block."
                ),
                "section": {"id": section.id, "name": section.name},
                "nearby_days": nearby_days,
                "minimum_task_count": 2,
                "task_count": len(candidates),
                "tasks": [
                    {
                        "id": task.id,
                        "task_id": task.task_id,
                        "asset": task.asset.name,
                        "due_date": str(task.due_date),
                        "duration_minutes": task.duration_minutes,
                    }
                    for task in candidates
                ],
                "recommended_slot": None,
                "applied": False,
                "batch_id": None,
                "block_window": None,
            }
            return Response(
                payload,
                status=(status.HTTP_409_CONFLICT if apply else status.HTTP_200_OK),
            )

        # One preparation/clearance buffer is needed for the whole possession,
        # rather than repeating it for every asset task.
        setup_buffer_minutes = 15
        combined_duration = (
            sum(task.duration_minutes for task in candidates) + setup_buffer_minutes
        )
        windows = []
        for service_date in (
            start_date + timedelta(days=offset)
            for offset in range((end_date - start_date).days + 1)
        ):
            windows.extend(find_feasible_windows(
                section=section,
                service_date=service_date,
                duration_minutes=combined_duration,
                task_id=anchor.task_id,
            ))
        best = (
            max(windows, key=lambda item: item.get("decision_score") or 0.0)
            if windows
            else None
        )
        recommended_slot = None
        if best:
            recommended_slot = {
                "start": timezone.localtime(best["start"]).strftime("%Y-%m-%d %H:%M:%S"),
                "end": timezone.localtime(best["end"]).strftime("%Y-%m-%d %H:%M:%S"),
                "duration_minutes": combined_duration,
                "decision_score": best.get("decision_score"),
            }

        batch = None
        block_window = None
        if apply:
            if not best:
                return Response({"error": "No shared conflict-free slot is available."}, status=400)
            with transaction.atomic():
                block_window = BlockWindow.objects.create(
                    section=section,
                    start_time=best["start"],
                    end_time=best["end"],
                    status=BlockWindow.Status.RESERVED,
                )
                batch = MaintenanceBatch.objects.create(
                    section=section,
                    block_window=block_window,
                    start_time=best["start"],
                    end_time=best["end"],
                    status=MaintenanceBatch.Status.SCHEDULED,
                )
                batch.tasks.set(candidates)
                for task in candidates:
                    task.status = MaintenanceTask.Status.SCHEDULED
                    task.shared_block_window = block_window
                    task.save()
                    MaintenanceLog.objects.create(
                        task=task,
                        task_code=task.task_id,
                        event=MaintenanceLog.Event.SCHEDULED,
                        status=task.status,
                        details={
                            "maintenance_batch_id": batch.id,
                            "block_window_id": block_window.id,
                        },
                    )

        return Response({
            "combined_eligible": True,
            "section": {"id": section.id, "name": section.name},
            "nearby_days": nearby_days,
            "combined_duration_minutes": combined_duration,
            "setup_buffer_minutes": setup_buffer_minutes,
            "task_count": len(candidates),
            "tasks": [
                {
                    "id": task.id,
                    "task_id": task.task_id,
                    "asset": task.asset.name,
                    "due_date": str(task.due_date),
                    "duration_minutes": task.duration_minutes,
                }
                for task in candidates
            ],
            "recommended_slot": recommended_slot,
            "applied": apply and batch is not None,
            "batch_id": batch.id if batch else None,
            "block_window": BlockWindowSerializer(block_window).data if block_window else None,
        }, status=status.HTTP_201_CREATED if batch else status.HTTP_200_OK)

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
        elif not target_bw and data.get("task_id"):
            target_bw = (
                BlockWindow.objects
                .select_related("section")
                .filter(task__task_id=data.get("task_id"))
                .order_by("-id")
                .first()
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
                    t = MaintenanceTask.objects.filter(task_id=task_id).first()
                    if t:
                        target_bw.task = t
                        target_bw.save()
                        if t.status in (
                            MaintenanceTask.Status.PENDING,
                            MaintenanceTask.Status.SCHEDULED,
                            MaintenanceTask.Status.DELAYED,
                        ):
                            t.status = MaintenanceTask.Status.SCHEDULED
                            t.save()

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

        delayed_recovery = (
            task.status == MaintenanceTask.Status.DELAYED
            or task.due_date < timezone.localdate()
        )
        original_service_date = service_date

        if service_date < timezone.localdate() and not delayed_recovery:
            return Response(
                {
                    "error": "Cannot recommend or schedule maintenance for an expired date.",
                    "date": str(service_date),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if delayed_recovery:
            service_date, windows = find_next_feasible_windows(
                section=section,
                start_date=timezone.localdate(),
                duration_minutes=task.duration_minutes,
                task_id=task.task_id,
            )
            if service_date is None:
                windows = []
        else:
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
                key=(
                    (lambda x: (x["start"], -(x.get("decision_score") or 0.0)))
                    if delayed_recovery
                    else (lambda x: x.get("decision_score") or 0.0)
                ),
                reverse=not delayed_recovery,
            )
            best = sorted_w[0]
            score_val = best.get("decision_score")
            best_start = timezone.localtime(best["start"])
            best_end = timezone.localtime(best["end"])
            best_slot = {
                "start": best_start.strftime("%Y-%m-%d %H:%M:%S"),
                "end": best_end.strftime("%Y-%m-%d %H:%M:%S"),
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
                task=task,
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
            if task.status in (
                MaintenanceTask.Status.PENDING,
                MaintenanceTask.Status.SCHEDULED,
                MaintenanceTask.Status.DELAYED,
            ):
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
            "original_date": str(original_service_date),
            "rescheduled_due_to_delay": delayed_recovery,
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
                (
                    f"Task missed its original deadline; AI selected the earliest feasible recovery slot on {service_date}: "
                    f"{best_slot['start']} - {best_slot['end']}."
                    if delayed_recovery else
                    f"AI identified {len(windows)} conflict-free slot(s) for task {task.task_id}. Optimal slot is {best_slot['start']} - {best_slot['end']}."
                )
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
        throttle_classes=[AIEndpointThrottle],
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
        throttle_classes=[AIEndpointThrottle],
    )
    def detail_recommendation(self, request, pk=None):
        block_window = self.get_object()
        return self._handle_recommendation(request, block_window=block_window)

    @action(
        detail=False,
        methods=["post"],
        url_path="feasible-windows",
        throttle_classes=[AIEndpointThrottle],
    )
    def feasible_windows(self, request):
        """Backward compatibility alias for feasible-windows"""
        return self._handle_recommendation(request)

    @action(
        detail=True,
        methods=["post"],
        url_path="apply-recommendation",
        throttle_classes=[AIEndpointThrottle],
    )
    def apply_recommendation(self, request, pk=None):
        """Backward compatibility alias for apply-recommendation"""
        block_window = self.get_object()
        return self._handle_recommendation(request, block_window=block_window)
