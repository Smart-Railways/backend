from datetime import timedelta

from apps.trains.models import TrainMovement


def find_train_conflicts(
    section,
    maintenance_start,
    maintenance_end,
):
    return TrainMovement.objects.filter(
        section=section,
        entry_time__lt=maintenance_end,
        exit_time__gt=maintenance_start,
    )


def find_feasible_windows(
    section,
    block_start,
    block_end,
    duration_minutes,
):
    movements = TrainMovement.objects.filter(
        section=section,
        entry_time__lt=block_end,
        exit_time__gt=block_start,
    ).order_by("entry_time")

    required_duration = timedelta(
        minutes=duration_minutes
    )

    windows = []
    current_time = block_start

    for movement in movements:

        # Limit train movement to the block boundaries
        train_start = max(
            movement.entry_time,
            block_start,
        )

        train_end = min(
            movement.exit_time,
            block_end,
        )

        # Check gap before this train
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

        # Move pointer past the train
        if train_end > current_time:
            current_time = train_end

    # Check gap after the last train
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