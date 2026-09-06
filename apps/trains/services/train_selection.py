from datetime import date

from apps.corridors.models import RailwaySection
from apps.trains.models import TrainSchedule


PREMIUM_KEYWORDS = (
    "VANDE BHARAT",
    "RAJDHANI",
    "SHATABDI",
    "TEJAS",
)

MAX_TRAINS = 40
MAX_PREMIUM_TRAINS = 10


def is_premium_train(train) -> bool:
    name = train.name.upper()

    return any(
        keyword in name
        for keyword in PREMIUM_KEYWORDS
    )


def get_relevant_train_numbers(
    service_date: date,
    max_per_section: int = 40,
) -> list[str]:
    day_index = service_date.weekday()

    sections = RailwaySection.objects.filter(
        is_active=True
    )

    premium_trains = set()
    regular_trains = set()

    for section in sections:

        schedules = (
            TrainSchedule.objects
            .filter(
                section=section,
                is_active=True,
            )
            .select_related("train")
        )

        section_count = 0

        for schedule in schedules:

            if schedule.running_days[day_index] != "1":
                continue

            train = schedule.train
            train_number = train.train_number

            if is_premium_train(train):
                premium_trains.add(train_number)
            else:
                regular_trains.add(train_number)

            section_count += 1

            if section_count >= max_per_section:
                break

    # ---------------------------------------------
    # Select maximum 10 premium trains
    # ---------------------------------------------

    selected_premium = list(premium_trains)[
        :MAX_PREMIUM_TRAINS
    ]

    # ---------------------------------------------
    # Fill remaining slots with regular trains
    # ---------------------------------------------

    remaining_slots = MAX_TRAINS - len(selected_premium)

    selected_regular = list(regular_trains)[
        :remaining_slots
    ]

    return selected_premium + selected_regular