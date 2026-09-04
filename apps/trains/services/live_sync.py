from datetime import datetime

from django.utils import timezone

from apps.corridors.models import RailwaySection

from ..models import Train, TrainMovement, TrainSchedule
from .railkit import RailKitClient
from .parser import parse_live_train_response


def parse_live_datetime(
    value: dict | str | None,
    service_date,
):
    """
    Convert RailKit time like '16:58 02-Sep', '03:25 04-Sep*',
    or {'actual': '03:25 04-Sep*', 'scheduled': '02:22 04-Sep'}
    into an aware Django datetime.
    """
    if not value:
        return None

    time_str = None
    if isinstance(value, dict):
        # Prefer actual, fallback to scheduled
        time_str = value.get("actual") or value.get("scheduled")
    elif isinstance(value, str):
        time_str = value

    if not time_str:
        return None

    # Clean any trailing '*' or whitespace (e.g., '03:25 04-Sep*')
    clean_val = str(time_str).replace("*", "").strip()

    try:
        dt = datetime.strptime(
            f"{clean_val} {service_date.year}",
            "%H:%M %d-%b %Y",
        )
        return timezone.make_aware(dt)
    except (ValueError, TypeError):
        try:
            parsed_time = datetime.strptime(clean_val, "%H:%M").time()
            combined = datetime.combine(service_date, parsed_time)
            return timezone.make_aware(combined)
        except Exception:
            return None



def sync_live_train(
    train_number: str,
    service_date,
) -> dict:

    client = RailKitClient()

    railkit_date = service_date.strftime("%d-%m-%Y")

    response = client.track_train(
        train_number,
        railkit_date,
    )

    parsed = parse_live_train_response(response)

    train = Train.objects.filter(
        train_number=train_number
    ).first()

    if not train:
        return {
            "train_number": train_number,
            "service_date": str(service_date),
            "error": f"Train {train_number} not found in database.",
            "updated_movements": [],
        }

    updated_movements = []

    for schedule in train.schedules.select_related("section"):

        section = schedule.section

        timeline = parsed["stoppages"]

        source = next(
            (
                station
                for station in timeline
                if station["stationCode"]
                == section.source_station_code
            ),
            None,
        )

        destination = next(
            (
                station
                for station in timeline
                if station["stationCode"]
                == section.destination_station_code
            ),
            None,
        )

        if not source or not destination:
            continue

        actual_entry = None
        actual_exit = None

        if source.get("departure"):
            actual_entry = parse_live_datetime(
                source["departure"],
                service_date,
            )

        if destination.get("arrival"):
            actual_exit = parse_live_datetime(
                destination["arrival"],
                service_date,
            )

        movement, created = TrainMovement.objects.update_or_create(
            schedule=schedule,
            service_date=service_date,
            defaults={
                "actual_entry_time": actual_entry,
                "actual_exit_time": actual_exit,
            },
        )

        updated_movements.append({
            "section": section.name,
            "movement_id": movement.id,
            "created": created,
        })

    return {
        "train_number": train_number,
        "service_date": str(service_date),
        "current_station": parsed["current_station_code"],
        "updated_movements": updated_movements,
    }