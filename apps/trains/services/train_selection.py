from datetime import date

from apps.corridors.models import RailwaySection
from apps.trains.models import TrainSchedule


PREMIUM_KEYWORDS = (
    "VANDE BHARAT",
    "RAJDHANI",
    "SHATABDI",
    "TEJAS",
)

MAX_TRAINS = 30
MAX_PREMIUM_TRAINS = 10


def is_premium_train(train) -> bool:
    name = train.name.upper().strip()

    return any(
        keyword in name
        for keyword in PREMIUM_KEYWORDS
    )


def get_relevant_train_numbers(
    service_date: date,
    max_per_section: int = 30,
) -> list[str]:
    """
    Return relevant trains that actually run on the given date.

    Trains that do not operate on service_date are excluded before
    any RailKit live-tracking request is created.
    """

    day_index = service_date.weekday()

    sections = RailwaySection.objects.filter(
        is_active=True
    ).order_by("id")

    premium_trains = {}
    regular_trains = {}

    for section in sections:

        schedules = (
            TrainSchedule.objects
            .filter(
                section=section,
                is_active=True,
            )
            .select_related("train")
            .order_by("train__train_number")
        )

        section_count = 0

        for schedule in schedules:

            # ---------------------------------------------
            # IMPORTANT:
            # Skip trains that do not run on this day.
            # ---------------------------------------------

            if schedule.running_days[day_index] != "1":
                continue

            train = schedule.train
            train_number = train.train_number

            if is_premium_train(train):
                premium_trains[train_number] = train
            else:
                regular_trains[train_number] = train

            section_count += 1

            if section_count >= max_per_section:
                break

    # ---------------------------------------------
    # Sort for deterministic selection
    # ---------------------------------------------

    premium_numbers = sorted(premium_trains.keys())
    regular_numbers = sorted(regular_trains.keys())

    # ---------------------------------------------
    # Select maximum 10 premium trains
    # ---------------------------------------------

    selected_premium = premium_numbers[:MAX_PREMIUM_TRAINS]

    # ---------------------------------------------
    # Fill remaining slots with regular trains
    # ---------------------------------------------

    remaining_slots = MAX_TRAINS - len(selected_premium)

    selected_regular = regular_numbers[:remaining_slots]

    return selected_premium + selected_regular