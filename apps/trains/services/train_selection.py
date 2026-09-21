from datetime import date

from apps.corridors.models import RailwaySection
from apps.trains.models import TrainSchedule


PREMIUM_KEYWORDS = (
    "VANDE BHARAT",
    "RAJDHANI",
    "SHATABDI",
    "TEJAS",
)

MAX_TRAINS_PER_SECTION = 10


def is_premium_train(train) -> bool:
    name = train.name.upper().strip()

    return any(
        keyword in name
        for keyword in PREMIUM_KEYWORDS
    )


def get_relevant_train_numbers(
    service_date: date,
    max_per_section: int = MAX_TRAINS_PER_SECTION,
) -> list[str]:
    """
    Select up to max_per_section trains from every active railway
    section for live tracking.

    Only trains running on service_date are considered.

    Premium trains are prioritised within each section.

    Train numbers are globally deduplicated before being returned,
    because the same train may pass through multiple sections.
    """

    day_index = service_date.weekday()

    sections = (
        RailwaySection.objects
        .filter(is_active=True)
        .order_by("id")
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
            .order_by("train__train_number")
        )

        premium_trains = []
        regular_trains = []

        for schedule in schedules:

            running_days = schedule.running_days

            if not running_days:
                continue

            if len(running_days) <= day_index:
                continue

            if running_days[day_index] != "1":
                continue

            train = schedule.train

            if is_premium_train(train):
                premium_trains.append(
                    train.train_number
                )
            else:
                regular_trains.append(
                    train.train_number
                )

        # Premium trains first, followed by regular trains.
        section_candidates = (
            premium_trains + regular_trains
        )

        # Maximum 10 trains for THIS section.
        section_selected = (
            section_candidates[:max_per_section]
        )

        # Globally deduplicate trains.
        for train_number in section_selected:
            selected_train_numbers.add(
                train_number
            )

    return sorted(selected_train_numbers)