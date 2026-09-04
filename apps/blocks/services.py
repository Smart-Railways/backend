from datetime import timedelta

from django.db.models import Q

from apps.trains.models import TrainMovement


def find_train_conflicts(
    section,
    maintenance_start,
    maintenance_end,
):
    """
    Find train movements that overlap with the
    requested maintenance window.
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


def find_feasible_windows(
    section,
    block_start,
    block_end,
    duration_minutes,
):
    """
    Find gaps between actual train movements
    where maintenance can safely be performed.
    """

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
        .select_related(
            "schedule",
            "schedule__train",
        )
        .order_by("actual_entry_time")
    )

    required_duration = timedelta(
        minutes=duration_minutes
    )

    windows = []
    current_time = block_start

    for movement in movements:

        train_start = max(
            movement.actual_entry_time,
            block_start,
        )

        # If the train hasn't exited yet,
        # treat the end of the block as occupied.
        train_end = (
            movement.actual_exit_time
            if movement.actual_exit_time
            else block_end
        )

        train_end = min(
            train_end,
            block_end,
        )

        # Gap before this train
        if train_start > current_time:

            gap_duration = train_start - current_time

            if gap_duration >= required_duration:
                windows.append({
                    "start": current_time,
                    "end": train_start,
                    "duration_minutes": int(
                        gap_duration.total_seconds() / 60
                    ),
                })

        # Move pointer past train
        if train_end > current_time:
            current_time = train_end

    # Gap after last train
    if current_time < block_end:

        gap_duration = block_end - current_time

        if gap_duration >= required_duration:
            windows.append({
                "start": current_time,
                "end": block_end,
                "duration_minutes": int(
                    gap_duration.total_seconds() / 60
                ),
            })

    return windows