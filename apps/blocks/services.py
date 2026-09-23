from datetime import datetime, time, timedelta
from math import ceil

from django.db.models import Q
from django.utils import timezone

from apps.blocks.ai_client import RailwayAIClient, AIClientError
from apps.maintenance.models import MaintenanceTask
from apps.trains.models import TrainMovement, TrainSchedule


def get_section_occupancies(section, service_date):
    """Return timetable passages with observed/live values overlaid when present."""
    day_index = service_date.weekday()
    tz = timezone.get_current_timezone()
    occupancies = []

    schedules = (
        TrainSchedule.objects.filter(section=section, is_active=True)
        .select_related("train")
        .prefetch_related("movements")
    )
    for schedule in schedules:
        if len(schedule.running_days) != 7 or schedule.running_days[day_index] != "1":
            continue

        scheduled_entry = timezone.make_aware(
            datetime.combine(service_date, schedule.scheduled_entry_time), tz
        )
        # Old timetable imports may have offset 0 for an end at midnight.
        # A non-increasing end time belongs to the following calendar day.
        exit_day_offset = schedule.scheduled_exit_day_offset
        if (
            not exit_day_offset
            and schedule.scheduled_exit_time <= schedule.scheduled_entry_time
        ):
            exit_day_offset = 1

        scheduled_exit = timezone.make_aware(
            datetime.combine(
                service_date + timedelta(days=exit_day_offset),
                schedule.scheduled_exit_time,
            ),
            tz,
        )
        movement = next(
            (
                item for item in schedule.movements.all()
                if item.service_date == service_date
            ),
            None,
        )
        occupancies.append({
            "entry": (
                movement.actual_entry_time
                if movement and movement.actual_entry_time
                else (
                    movement.estimated_entry_time
                    if movement and movement.estimated_entry_time
                    else scheduled_entry
                )
            ),
            "exit": (
                movement.actual_exit_time
                if movement and movement.actual_exit_time
                else (
                    movement.estimated_exit_time
                    if movement and movement.estimated_exit_time
                    else scheduled_exit
                )
            ),
        })

    return sorted(occupancies, key=lambda item: item["entry"])


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
    Calculate a deterministic fallback score when Railway-AI is unavailable.
    """
    if not task:
        return 0.50

    urgency_map = {
        "CRITICAL": 0.9,
        "HIGH": 0.7,
        "MEDIUM": 0.5,
        "LOW": 0.3,
    }
    urgency = urgency_map.get(task.priority, 0.5)
    crit = min(1.0, getattr(task.asset, "criticality", 3) / 5.0)
    dur = min(1.0, task.duration_minutes / 180.0)
    score = (0.20 * urgency) + (0.15 * crit) + (0.05 * dur) + 0.10
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

    ist = timezone.get_current_timezone()
    today = timezone.localdate()

    # Never produce a recommendation for a date that has already passed.
    # This protects every caller, including the embedded ML optimiser.
    if service_date < today:
        return []

    # Use a half-open day [00:00, next day 00:00), not time.max.  That makes
    # a slot ending at exactly 00:00 of the next day valid.

    block_start = timezone.make_aware(
        datetime.combine(
            service_date,
            time.min,
        ),
        timezone=ist,
    )

    block_end = timezone.make_aware(
        datetime.combine(
            service_date + timedelta(days=1),
            time.min,
        ),
        timezone=ist,
    )

    planning_start = block_start
    if service_date == today:
        now = timezone.localtime(timezone.now(), ist)
        # Slot durations are in 30 minute increments. Begin strictly in the
        # future, never in a partly elapsed slot.
        rounded_now = now.replace(second=0, microsecond=0)
        planning_start = rounded_now + timedelta(
            minutes=30 - (rounded_now.minute % 30)
        )
        planning_start = max(block_start, planning_start)
        if planning_start >= block_end:
            return []

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
    # Try the bundled Railway-AI optimizer first.
    # ---------------------------------------------------------
    if task and RailwayAIClient.is_healthy():
        try:
            ai_result = RailwayAIClient.optimize_maintenance_blocks(
                tasks=[{
                    "task_id": task.task_id,
                    "section_id": section.id,
                    "estimated_duration": task.duration_minutes,
                    "required_manpower": 2,
                    "criticality": task.asset.criticality,
                    "priority": task.priority,
                    "urgency_score": {
                        "CRITICAL": 0.9,
                        "HIGH": 0.7,
                        "MEDIUM": 0.5,
                        "LOW": 0.3,
                    }.get(task.priority, 0.5),
                    "failure_probability": 0.0,
                    "predicted_delay_minutes": 0.0,
                }],
                block_windows=[{
                    "block_id": f"VIRTUAL-BW-{section.id}",
                    "section_id": section.id,
                }],
                planning_hours=max(
                    1,
                    ceil((block_end - planning_start).total_seconds() / 3600),
                ),
            )
            windows = []
            for allocation in ai_result.get("allocations", []):
                start = planning_start + timedelta(
                    minutes=int(allocation.get("start_slot", 0)) * 30
                )
                duration = int(allocation.get("duration_minutes", duration_minutes))
                end = start + timedelta(minutes=duration)
                if end <= block_end:
                    windows.append({
                        "start": start,
                        "end": end,
                        "duration_minutes": duration,
                        "decision_score": allocation.get(
                            "maintenance_decision_score", 0.0
                        ),
                        "algorithm": "Embedded Railway-AI CP-SAT",
                    })
            if windows:
                return windows

        except AIClientError:
            # AI unavailable → use deterministic fallback.
            pass

    # ---------------------------------------------------------
    # Heuristic fallback
    # ---------------------------------------------------------

    occupancies = get_section_occupancies(section, service_date)

    required_duration = timedelta(
        minutes=duration_minutes
    )

    fallback_decision_score = (
        calculate_task_decision_score(task, section)
        if task
        else None
    )

    windows = []

    current_time = planning_start

    for occupancy in occupancies:

        if occupancy["entry"] >= block_end or occupancy["exit"] <= block_start:
            continue

        train_start = max(
            occupancy["entry"],
            block_start,
        )

        train_end = min(
            occupancy["exit"],
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


def find_next_feasible_windows(
    section,
    start_date,
    duration_minutes,
    task_id=None,
    max_days=14,
):
    """Return windows on the earliest feasible date from ``start_date``.

    This is used for overdue maintenance: its original deadline must never be
    reused as a planning date, but the work should be recovered in the first
    current or future slot that the timetable allows.
    """
    candidate_date = max(start_date, timezone.localdate())
    for day_offset in range(max_days + 1):
        service_date = candidate_date + timedelta(days=day_offset)
        windows = find_feasible_windows(
            section=section,
            service_date=service_date,
            duration_minutes=duration_minutes,
            task_id=task_id,
        )
        if windows:
            return service_date, windows
    return None, []


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

    # 3. Find feasible conflict-free windows. A delayed task is recovered from
    # today onward, not from the expired date of its old block window.
    delayed_recovery = bool(
        task
        and (
            task.status == MaintenanceTask.Status.DELAYED
            or task.due_date < timezone.localdate()
        )
    )
    if delayed_recovery:
        recommendation_date, feasible_windows = find_next_feasible_windows(
            section=section,
            start_date=timezone.localdate(),
            duration_minutes=required_duration,
            task_id=task.task_id,
        )
    else:
        recommendation_date = service_date
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

    if delayed_recovery:
        # For overdue work, recover it at the earliest safe opportunity;
        # score breaks ties between simultaneous candidates.
        scored_windows.sort(key=lambda x: (x[2]["start"], -x[0]))
    else:
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
        "recommendation_date": str(recommendation_date) if recommendation_date else None,
        "rescheduled_due_to_delay": delayed_recovery,
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
