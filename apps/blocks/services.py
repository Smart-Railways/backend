# backend-main (1)/backend-main/apps/blocks/services.py
from datetime import timedelta
from django.db.models import Q
from django.utils import timezone
from apps.trains.models import TrainMovement
from apps.maintenance.models import MaintenanceTask
from apps.blocks.ai_client import RailwayAIClient, AIClientError

def find_train_conflicts(section, maintenance_start, maintenance_end):
    """
    Find train movements overlapping with the requested maintenance window.
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
        .select_related("schedule", "schedule__train")
        .order_by("actual_entry_time")
    )

def find_feasible_windows(section, block_start, block_end, duration_minutes, task_id=None):
    """
    Calculates feasible windows. If task_id is provided and AI service is online,
    invokes the CP-SAT Block Optimizer. Otherwise falls back to interval gap logic.
    """
    # 1. Check if AI Optimizer is reachable
    if RailwayAIClient.is_healthy():
        try:
            # Query pending tasks on this section
            tasks_qs = MaintenanceTask.objects.filter(
                asset__section=section,
                status=MaintenanceTask.Status.PENDING
            ).select_related("asset")

            if task_id:
                tasks_qs = tasks_qs.filter(task_id=task_id)

            tasks_payload = []
            for t in tasks_qs:
                tasks_payload.append({
                    "task_id": t.task_id,
                    "section_id": section.id,
                    "estimated_duration": t.duration_minutes,
                    "required_manpower": 6,
                    "criticality": getattr(t.asset, "criticality", 3),
                    "priority": t.priority,
                    "urgency_score": 0.9 if t.priority == "CRITICAL" else 0.6,
                    "failure_probability": 0.45,
                    "predicted_delay_minutes": 10.0
                })

            if tasks_payload:
                hours = max(1, int((block_end - block_start).total_seconds() / 3600))
                block_payload = [{
                    "block_id": f"BW-{section.id}",
                    "section_id": section.id,
                    "start_time": block_start.strftime("%Y-%m-%d %H:%M:%S"),
                    "end_time": block_end.strftime("%Y-%m-%d %H:%M:%S")
                }]

                ai_result = RailwayAIClient.optimize_maintenance_blocks(
                    tasks=tasks_payload,
                    block_windows=block_payload,
                    planning_hours=hours
                )

                # Format AI output into frontend window slots
                windows = []
                for alloc in ai_result.get("allocations", []):
                    slot_start = block_start + timedelta(minutes=alloc.get("start_slot", 0) * 30)
                    slot_end = slot_start + timedelta(minutes=alloc.get("duration_minutes", duration_minutes))
                    windows.append({
                        "start": slot_start,
                        "end": slot_end,
                        "duration_minutes": alloc.get("duration_minutes", duration_minutes),
                        "decision_score": alloc.get("maintenance_decision_score", 0.85),
                        "algorithm": "CP-SAT Constraint Solver"
                    })

                if windows:
                    return windows
        except AIClientError:
            pass  # Fall back to heuristic interval gaps below

    # 2. Heuristic Interval Gap Fallback
    movements = (
        TrainMovement.objects
        .filter(
            schedule__section=section,
            service_date=block_start.date(),
            actual_entry_time__lt=block_end,
        )
        .filter(
            Q(actual_exit_time__isnull=True)
            | Q(actual_exit_time__gt=block_start)
        )
        .order_by("actual_entry_time")
    )

    required_duration = timedelta(minutes=duration_minutes)
    windows = []
    current_time = block_start

    for movement in movements:
        train_start = max(movement.actual_entry_time, block_start)
        train_end = movement.actual_exit_time if movement.actual_exit_time else block_end
        train_end = min(train_end, block_end)

        if train_start > current_time:
            gap_duration = train_start - current_time
            if gap_duration >= required_duration:
                windows.append({
                    "start": current_time,
                    "end": train_start,
                    "duration_minutes": int(gap_duration.total_seconds() / 60),
                    "algorithm": "Database Timestamp Gap"
                })

        if train_end > current_time:
            current_time = train_end

    if current_time < block_end:
        gap_duration = block_end - current_time
        if gap_duration >= required_duration:
            windows.append({
                "start": current_time,
                "end": block_end,
                "duration_minutes": int(gap_duration.total_seconds() / 60),
                "algorithm": "Database Timestamp Gap"
            })

    return windows