from datetime import datetime, time, timedelta

from django.utils import timezone

from ..models import Train, TrainMovement
from .railway_client import RailKitClient, RailKitError
from .parser import parse_train_response


def parse_scheduled_datetime(
    time_value: time | str | None,
    service_date,
    day_offset: int = 0,
):
    """
    Convert a scheduled time such as "10:08" into an aware
    Django datetime.

    day_offset is used for scheduled sections that exit after midnight.
    """

    if not time_value:
        return None

    try:
        parsed_time = (
            time_value
            if isinstance(time_value, time)
            else datetime.strptime(time_value, "%H:%M").time()
        )

        target_date = service_date + timedelta(
            days=day_offset
        )

        combined = datetime.combine(
            target_date,
            parsed_time,
        )

        return timezone.make_aware(
            combined,
            timezone.get_current_timezone(),
        )

    except (ValueError, TypeError):
        return None


def sync_live_train(
    train_number: str,
    service_date,
) -> dict:
    """
    Fetch combined train information from the local Node railway
    service and calculate estimated section movement using the
    current reported delay.

    Endpoint used:

        /train/{train_number}?date=DD-MM-YYYY
    """

    train = (
        Train.objects
        .filter(train_number=train_number)
        .first()
    )

    if not train:
        return {
            "train_number": train_number,
            "service_date": str(service_date),
            "error": (
                f"Train {train_number} "
                "not found in database."
            ),
            "delay_minutes": None,
            "status_label": None,
            "updated_movements": [],
        }

    try:
        response = RailKitClient().get_train(
            train_number,
            service_date.strftime("%d-%m-%Y"),
        )
        parsed = parse_train_response(response)
    except (RailKitError, ValueError, TypeError) as exc:
        # Preserve previous movement data when the service is unavailable or
        # returns malformed payloads.
        return {
            "train_number": train_number,
            "service_date": str(service_date),
            "error": str(exc),
            "delay_minutes": None,
            "status_label": None,
            "updated_movements": [],
        }

    # --------------------------------------------------
    # Live delay
    # --------------------------------------------------

    delay_minutes = parsed.get(
        "delay_minutes"
    )

    status_label = parsed.get(
        "status_label"
    )

    # A missing delay is not evidence that the train is on time. Preserve any
    # existing movement record rather than replacing it with unknown values.
    if delay_minutes is None:
        return {
            "train_number": train_number,
            "train_name": parsed.get("train_name"),
            "service_date": str(service_date),
            "delay_minutes": None,
            "status_label": status_label,
            "updated_movements": [],
            "skipped": "UNKNOWN_LIVE_STATUS",
        }

    updated_movements = []

    # --------------------------------------------------
    # Process every corridor section used by this train
    # --------------------------------------------------

    schedules = (
        train.schedules
        .select_related("section")
        .filter(is_active=True)
    )

    if not schedules.exists():
        return {
            "train_number": train_number,
            "train_name": parsed.get("train_name"),
            "service_date": str(service_date),
            "delay_minutes": delay_minutes,
            "status_label": status_label,
            "updated_movements": [],
            "skipped": "NO_ACTIVE_SCHEDULES",
        }

    day_index = service_date.weekday()
    for schedule in schedules:
        if (
            len(schedule.running_days) != 7
            or schedule.running_days[day_index] != "1"
        ):
            continue

        scheduled_entry = parse_scheduled_datetime(
            schedule.scheduled_entry_time,
            service_date,
        )
        exit_day_offset = schedule.scheduled_exit_day_offset
        if (
            not exit_day_offset
            and schedule.scheduled_exit_time <= schedule.scheduled_entry_time
        ):
            exit_day_offset = 1

        scheduled_exit = parse_scheduled_datetime(
            schedule.scheduled_exit_time,
            service_date,
            day_offset=exit_day_offset,
        )

        # --------------------------------------------------
        # Apply current live delay
        # --------------------------------------------------

        estimated_entry = None
        estimated_exit = None

        if delay_minutes is not None and scheduled_entry:
            estimated_entry = (
                scheduled_entry + timedelta(minutes=delay_minutes)
            )

        if delay_minutes is not None and scheduled_exit:
            estimated_exit = (
                scheduled_exit + timedelta(minutes=delay_minutes)
            )

        # --------------------------------------------------
        # IMPORTANT
        #
        # We are NOT writing estimated times into
        # actual_entry_time / actual_exit_time.
        #
        # /train gives us current delay, not observed
        # actual station timestamps.
        # --------------------------------------------------

        movement, created = TrainMovement.objects.update_or_create(
            schedule=schedule,
            service_date=service_date,
            defaults={
                "estimated_entry_time": estimated_entry,
                "estimated_exit_time": estimated_exit,
                "delay_minutes": delay_minutes,
                "status_label": status_label,
                "last_live_update": timezone.now(),
            },
        )

        updated_movements.append({
            "section": schedule.section.name,
            "movement_id": movement.id,
            "created": created,

            "scheduled_entry": (
                scheduled_entry.isoformat()
                if scheduled_entry
                else None
            ),

            "scheduled_exit": (
                scheduled_exit.isoformat()
                if scheduled_exit
                else None
            ),

            "estimated_entry": (
                estimated_entry.isoformat()
                if estimated_entry
                else None
            ),

            "estimated_exit": (
                estimated_exit.isoformat()
                if estimated_exit
                else None
            ),
        })

    return {
        "train_number": train_number,
        "train_name": parsed.get(
            "train_name"
        ),
        "service_date": str(service_date),

        "delay_minutes": delay_minutes,
        "status_label": status_label,

        "updated_movements": updated_movements,
    }
