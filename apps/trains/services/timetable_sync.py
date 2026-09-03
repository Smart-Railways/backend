from django.db import transaction

from apps.corridors.models import RailwaySection

from ..models import Train, TrainSchedule
from .railkit import RailKitClient
from .timetable_parser import parse_timetable_response


@transaction.atomic
def sync_timetable_for_section(section: RailwaySection) -> dict:
    """
    Fetch RailKit timetable data for one railway section
    and synchronize Train + TrainSchedule records.
    """

    client = RailKitClient()

    response = client.search_trains_between_stations(
        section.source_station_code,
        section.destination_station_code,
    )

    trains = parse_timetable_response(response)

    trains_created = 0
    trains_updated = 0
    schedules_created = 0
    schedules_updated = 0

    for train_data in trains:

        # -------------------------------------------------
        # 1. Create / update Train
        # -------------------------------------------------

        train, train_created = Train.objects.update_or_create(
            train_number=train_data["train_number"],
            defaults={
                "name": train_data["train_name"],
                "train_type": Train.TrainType.EXPRESS,
            },
        )

        if train_created:
            trains_created += 1
        else:
            trains_updated += 1

        # -------------------------------------------------
        # 2. Create / update TrainSchedule
        # -------------------------------------------------

        _, schedule_created = TrainSchedule.objects.update_or_create(
            train=train,
            section=section,
            defaults={
                "scheduled_entry_time": train_data[
                    "scheduled_entry_time"
                ],
                "scheduled_exit_time": train_data[
                    "scheduled_exit_time"
                ],
                "scheduled_exit_day_offset": train_data.get(
                    "scheduled_exit_day_offset", 0
                ),
                "running_days": train_data.get("running_days", "1111111"),
                "is_active": True,
            },
        )

        if schedule_created:
            schedules_created += 1
        else:
            schedules_updated += 1

    return {
        "section": section.name,
        "trains_received": len(trains),
        "trains_created": trains_created,
        "trains_updated": trains_updated,
        "schedules_created": schedules_created,
        "schedules_updated": schedules_updated,
    }