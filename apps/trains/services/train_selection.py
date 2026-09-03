from datetime import date

from django.db.models import Q

from apps.corridors.models import RailwaySection
from apps.trains.models import TrainSchedule


def get_relevant_train_numbers(
    service_date: date,
    max_per_section: int = 40,
) -> list[str]:
    """
    Select trains that are relevant for live tracking today.

    Maximum of `max_per_section` trains are selected per active section.
    Train numbers are deduplicated because one RailKit tracking request
    gives the train's movement across its route.
    """

    day_index = service_date.weekday()

    sections = RailwaySection.objects.filter(
        is_active=True
    )

    selected_train_numbers = set()

    for section in sections:
        schedules = (
            TrainSchedule.objects
            .filter(
                section=section,
                is_active=True,
            )
            .select_related("train")
        )

        section_trains = []

        for schedule in schedules:
            if schedule.running_days[day_index] != "1":
                continue

            section_trains.append(
                schedule.train.train_number
            )

            if len(section_trains) >= max_per_section:
                break

        selected_train_numbers.update(section_trains)

    return list(selected_train_numbers)