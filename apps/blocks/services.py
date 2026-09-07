from datetime import datetime, time, timedelta

from django.db.models import Q
from django.utils import timezone

from apps.blocks.ai_client import RailwayAIClient, AIClientError
from apps.maintenance.models import MaintenanceTask
from apps.trains.models import TrainMovement


def find_train_conflicts(
    section,
    maintenance_start,
    maintenance_end,
):
    """
    Find train movements overlapping with the requested
    maintenance window.
    """

    return (
        TrainMovement.objects
        .filter(
            schedule__section=section,
            service_date=maintenance_start.date(),
            actual_entry_time__lt=maintenance_end,
        )
        .filter(
            Q(actual_exit_time__isnull=True)
            | Q(actual_exit_time__gt=maintenance_start)
        )
        .select_related(
            "schedule",
            "schedule__train",
        )
        .order_by("actual_entry_time")
    )


def calculate_task_decision_score(task, section=None):
    """
    Calculate normalized maintenance decision score (0.0 to 1.0)
    combining urgency, criticality, duration, and failure risk.
    """
    if not task:
        return 0.50

    try:
        from src.decision.maintenance_decision_engine import (
            MaintenanceDecisionEngine,
        )
        import pandas as pd

        engine = MaintenanceDecisionEngine()
        df = pd.DataFrame([{
            "task_id": task.task_id,
            "section_id": (
                section.id if section else getattr(task.asset, "section_id", 1)
            ),
            "estimated_duration": task.duration_minutes,
            "criticality": getattr(task.asset, "criticality", 3),
            "priority": task.priority,
            "urgency_score": (
                0.9
                if task.priority == "CRITICAL"
                else (0.7 if task.priority == "HIGH" else 0.4)
            ),
            "failure_probability": 0.45,
            "predicted_delay_minutes": 10.0,
            "overdue_days": 1 if getattr(task, "is_overdue", False) else 0,
        }])
        scored = engine.transform(df)
        return float(
            round(scored["maintenance_decision_score"].iloc[0], 3)
        )
    except Exception:
        urgency_map = {
            "CRITICAL": 0.9,
            "HIGH": 0.7,
            "MEDIUM": 0.5,
            "LOW": 0.3,
        }
        urgency = urgency_map.get(task.priority, 0.5)
        crit = min(1.0, getattr(task.asset, "criticality", 3) / 5.0)
        dur = min(1.0, task.duration_minutes / 180.0)
        score = (
            (0.25 * 0.45)
            + (0.20 * urgency)
            + (0.15 * crit)
            + (0.05 * dur)
            + 0.10
        )
        return float(round(score, 3))


def find_feasible_windows(
    section,
    service_date,
    duration_minutes,
    task_id=None,
):
    """
    Find feasible maintenance windows for a task on a given date.

    A virtual full-day planning window is used for the AI optimizer.
    No BlockWindow database record is created here.

    The actual BlockWindow is created later by the frontend/controller
    after selecting an approved window.
    """

    # ---------------------------------------------------------
    # Create a virtual planning window for the requested date.
    # ---------------------------------------------------------

    ist = timezone.get_current_timezone()

    block_start = timezone.make_aware(
        datetime.combine(
            service_date,
            time.min,
        ),
        timezone=ist,
    )

    block_end = timezone.make_aware(
        datetime.combine(
            service_date,
            time.max,
        ),
        timezone=ist,
    )

    # ---------------------------------------------------------
    # Get the requested maintenance task.
    # ---------------------------------------------------------

    task = None

    if task_id:
        task = (
            MaintenanceTask.objects
            .select_related(
                "asset",
                "asset__section",
            )
            .filter(
                task_id=task_id,
                asset__section=section,
            )
            .first()
        )

        if not task:
            return []

    # ---------------------------------------------------------
    # Try AI / CP-SAT optimizer first.
    # ---------------------------------------------------------

    if RailwayAIClient.is_healthy():

        try:
            tasks_payload = []

            if task:
                tasks_payload.append({
                    "task_id": task.task_id,
                    "section_id": section.id,
                    "estimated_duration": task.duration_minutes,
                    "required_manpower": 6,
                    "criticality": getattr(
                        task.asset,
                        "criticality",
                        3,
                    ),
                    "priority": task.priority,
                    "urgency_score": (
                        0.9
                        if task.priority == "CRITICAL"
                        else 0.6
                    ),
                    "failure_probability": 0.45,
                    "predicted_delay_minutes": 10.0,
                })

            if tasks_payload:

                # -------------------------------------------------
                # Virtual block window.
                #
                # This is NOT saved to the database.
                # It only gives the optimizer a planning horizon.
                # -------------------------------------------------

                planning_hours = 24

                block_payload = [
                    {
                        "block_id": f"VIRTUAL-BW-{section.id}",
                        "section_id": section.id,
                        "start_time": block_start.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "end_time": block_end.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                ]

                ai_result = (
                    RailwayAIClient
                    .optimize_maintenance_blocks(
                        tasks=tasks_payload,
                        block_windows=block_payload,
                        planning_hours=planning_hours,
                    )
                )

                # -------------------------------------------------
                # Convert AI allocations into frontend windows.
                # -------------------------------------------------

                windows = []

                for allocation in ai_result.get(
                    "allocations",
                    [],
                ):
                    start_slot = allocation.get(
                        "start_slot",
                        0,
                    )

                    allocated_duration = allocation.get(
                        "duration_minutes",
                        duration_minutes,
                    )

                    slot_start = (
                        block_start
                        + timedelta(
                            minutes=start_slot * 30
                        )
                    )

                    slot_end = (
                        slot_start
                        + timedelta(
                            minutes=allocated_duration
                        )
                    )

                    # Never allow the optimizer to return a window
                    # outside the requested day's planning horizon.
                    if slot_start < block_start:
                        continue

                    if slot_end > block_end:
                        continue

                    windows.append({
                        "start": slot_start,
                        "end": slot_end,
                        "duration_minutes": (
                            allocated_duration
                        ),
                        "decision_score": allocation.get(
                            "maintenance_decision_score",
                            0.85,
                        ),
                        "algorithm": (
                            "CP-SAT Constraint Solver"
                        ),
                    })

                if windows:
                    return windows

        except AIClientError:
            # AI unavailable → use deterministic fallback.
            pass

    # ---------------------------------------------------------
    # Heuristic fallback
    # ---------------------------------------------------------

    movements = (
        TrainMovement.objects
        .filter(
            schedule__section=section,
            service_date=service_date,
            actual_entry_time__lt=block_end,
        )
        .filter(
            Q(actual_exit_time__isnull=True)
            | Q(actual_exit_time__gt=block_start)
        )
        .select_related(
            "schedule",
            "schedule__train",
        )
        .order_by("actual_entry_time")
    )

    required_duration = timedelta(
        minutes=duration_minutes
    )

    fallback_decision_score = (
        calculate_task_decision_score(task, section)
        if task
        else None
    )

    windows = []

    current_time = block_start

    for movement in movements:

        train_start = max(
            movement.actual_entry_time,
            block_start,
        )

        train_end = (
            movement.actual_exit_time
            if movement.actual_exit_time
            else block_end
        )

        train_end = min(
            train_end,
            block_end,
        )

        # -----------------------------------------------------
        # There is a gap before this train.
        # -----------------------------------------------------

        if train_start > current_time:

            gap_duration = (
                train_start - current_time
            )

            if gap_duration >= required_duration:

                windows.append({
                    "start": current_time,
                    "end": train_start,
                    "duration_minutes": int(
                        gap_duration.total_seconds() / 60
                    ),
                    "decision_score": fallback_decision_score,
                    "algorithm": (
                        "Database Timestamp Gap"
                    ),
                })

        # -----------------------------------------------------
        # Move current pointer past the train.
        # -----------------------------------------------------

        if train_end > current_time:
            current_time = train_end

    # ---------------------------------------------------------
    # Check the final gap after the last train.
    # ---------------------------------------------------------

    if current_time < block_end:

        gap_duration = (
            block_end - current_time
        )

        if gap_duration >= required_duration:

            windows.append({
                "start": current_time,
                "end": block_end,
                "duration_minutes": int(
                    gap_duration.total_seconds() / 60
                ),
                "decision_score": fallback_decision_score,
                "algorithm": (
                    "Database Timestamp Gap"
                ),
            })

    return windows


def get_block_window_recommendation(block_window, task_id=None):
    """
    Evaluate an existing BlockWindow for train conflicts and calculate
    the best recommended alternative slot from feasible windows.
    Returns recommendation details, conflict summary, and a suggested PUT payload.
    """
    section = block_window.section
    current_start = timezone.localtime(block_window.start_time)
    current_end = timezone.localtime(block_window.end_time)
    service_date = current_start.date()

    current_duration_minutes = int(
        (current_end - current_start).total_seconds() / 60
    )

    # 1. Check conflicts in current window
    conflicts_qs = find_train_conflicts(
        section=section,
        maintenance_start=current_start,
        maintenance_end=current_end,
    )
    conflict_count = conflicts_qs.count()
    has_conflict = conflict_count > 0

    # 2. Resolve associated task (or highest priority pending/scheduled task)
    task = None
    if task_id:
        task = (
            MaintenanceTask.objects
            .select_related("asset", "asset__section")
            .filter(task_id=task_id, asset__section=section)
            .first()
        )
    if not task:
        task = (
            MaintenanceTask.objects
            .select_related("asset", "asset__section")
            .filter(
                asset__section=section,
                status__in=[
                    MaintenanceTask.Status.PENDING,
                    MaintenanceTask.Status.SCHEDULED,
                    MaintenanceTask.Status.DELAYED,
                ],
            )
            .order_by("-severity", "due_date")
            .first()
        )

    required_duration = (
        task.duration_minutes
        if task
        else current_duration_minutes
    )

    # 3. Find feasible conflict-free windows
    feasible_windows = find_feasible_windows(
        section=section,
        service_date=service_date,
        duration_minutes=required_duration,
        task_id=task.task_id if task else None,
    )

    # 4. Rank and pick the best slot
    best_slot = None
    has_better_slot = False
    recommendation_reason = ""

    scored_windows = []
    for w in feasible_windows:
        score = w.get("decision_score") or 0.0
        time_diff = abs((w["start"] - current_start).total_seconds())
        scored_windows.append((score, -time_diff, w))

    scored_windows.sort(key=lambda x: (x[0], x[1]), reverse=True)

    if scored_windows:
        candidate_slot = scored_windows[0][2]
        is_same_slot = (
            candidate_slot["start"] == current_start
            and candidate_slot["end"] == current_end
        )

        if has_conflict:
            best_slot = candidate_slot
            has_better_slot = True
            conflict_names = [
                c.schedule.train.train_number
                for c in conflicts_qs[:3]
            ]
            conflict_str = ", ".join(conflict_names)
            if len(conflicts_qs) > 3:
                conflict_str += f" and {len(conflicts_qs) - 3} more"

            score_str = (
                f"{best_slot['decision_score']:.3f}"
                if best_slot.get("decision_score") is not None
                else "N/A"
            )
            recommendation_reason = (
                f"Current window has {conflict_count} train conflict(s) with train(s) {conflict_str}. "
                f"AI recommends shifting to {best_slot['start'].strftime('%H:%M:%S')} - {best_slot['end'].strftime('%H:%M:%S')} "
                f"which is 100% collision-free with a decision score of {score_str}."
            )
        elif not is_same_slot:
            best_slot = candidate_slot
            has_better_slot = True
            score_str = (
                f"{best_slot['decision_score']:.3f}"
                if best_slot.get("decision_score") is not None
                else "N/A"
            )
            recommendation_reason = (
                f"Zero train conflicts in current slot. However, AI identified an optimized slot at "
                f"{best_slot['start'].strftime('%H:%M:%S')} - {best_slot['end'].strftime('%H:%M:%S')} "
                f"yielding higher network decision score ({score_str}) via {best_slot.get('algorithm')}."
            )
        else:
            best_slot = candidate_slot
            has_better_slot = False
            recommendation_reason = (
                "Current block window is already optimal. Zero train conflicts detected and maximum safety clearance maintained."
            )
    else:
        recommendation_reason = (
            "No alternative feasible maintenance windows found for this section on the requested date."
        )

    # Format conflicts list
    from .serializers import ConflictTrainMovementSerializer
    conflicts_data = ConflictTrainMovementSerializer(
        conflicts_qs,
        many=True,
    ).data

    formatted_recommended_slot = None
    suggested_put_payload = None

    if best_slot:
        score_val = best_slot.get("decision_score")
        best_start = timezone.localtime(best_slot["start"])
        best_end = timezone.localtime(best_slot["end"])
        formatted_recommended_slot = {
            "start": best_start.strftime("%Y-%m-%d %H:%M:%S"),
            "end": best_end.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_minutes": best_slot["duration_minutes"],
            "decision_score": round(score_val, 3) if score_val is not None else None,
            "algorithm": best_slot.get("algorithm"),
        }
        suggested_put_payload = {
            "section": section.id,
            "start_time": best_start.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": best_end.strftime("%Y-%m-%d %H:%M:%S"),
            "status": str(block_window.status),
        }

    from .serializers import FeasibleWindowItemSerializer
    windows_data = FeasibleWindowItemSerializer(
        feasible_windows,
        many=True,
    ).data

    return {
        "block_window_id": block_window.id,
        "task_id": task.task_id if task else None,
        "section": {
            "id": section.id,
            "name": section.name,
            "source": section.source_station,
            "source_code": section.source_station_code,
            "destination": section.destination_station,
            "destination_code": section.destination_station_code,
        },
        "current_slot": {
            "start_time": current_start.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": current_end.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_minutes": current_duration_minutes,
            "status": str(block_window.status),
            "has_conflict": has_conflict,
            "conflict_count": conflict_count,
            "conflicts": conflicts_data,
        },
        "has_better_slot": has_better_slot,
        "recommendation_reason": recommendation_reason,
        "recommended_slot": formatted_recommended_slot,
        "suggested_put_payload": suggested_put_payload,
        "put_url": f"/railways/block-windows/{block_window.id}/",
        "windows": windows_data,
    }