from datetime import date

from apps.corridors.models import RailwaySection
from apps.trains.models import TrainSchedule


PREMIUM_KEYWORDS = (
    "VANDE BHARAT",
    "RAJDHANI",
    "SHATABDI",
    "TEJAS",
)

MAX_TRAINS_PER_SECTION = 30
MAX_PREMIUM_TRAINS_PER_SECTION = 10
PREMIUM_PRIORITY_THRESHOLD = 7


def is_premium_train(train) -> bool:
    name = train.name.upper().strip()
    has_premium_name = any(keyword in name for keyword in PREMIUM_KEYWORDS)
    return train.priority > PREMIUM_PRIORITY_THRESHOLD or has_premium_name


def get_relevant_train_numbers(
    service_date: date,
    max_per_section: int = MAX_TRAINS_PER_SECTION,
) -> list[str]:
    """
    Select up to max_per_section trains from every active railway
    section for live tracking.

    Only trains running on service_date are considered.

    Up to 10 premium trains (priority above 7 or a premium name keyword) are
    selected first within each section. Remaining slots are filled by other
    operating trains up to max_per_section.

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
        section_train_numbers = set()

        for schedule in schedules:

            running_days = schedule.running_days

            if not running_days:
                continue

            if len(running_days) <= day_index:
                continue

            if running_days[day_index] != "1":
                continue

            train = schedule.train

            if train.train_number in section_train_numbers:
                continue
            section_train_numbers.add(train.train_number)

            if is_premium_train(train):
                premium_trains.append(train)
            else:
                regular_trains.append(train)

        premium_trains.sort(key=lambda train: (-train.priority, train.train_number))
        regular_trains.sort(key=lambda train: (-train.priority, train.train_number))

        premium_limit = min(MAX_PREMIUM_TRAINS_PER_SECTION, max_per_section)
        section_selected = premium_trains[:premium_limit]
        remaining_slots = max_per_section - len(section_selected)
        section_selected.extend(regular_trains[:remaining_slots])

        # If fewer regular services operate on this day, use additional
        # premium services rather than leaving live-sync capacity unused.
        if len(section_selected) < max_per_section:
            section_selected.extend(
                premium_trains[premium_limit:max_per_section]
            )

        # Globally deduplicate trains.
        selected_train_numbers.update(train.train_number for train in section_selected)

    return sorted(selected_train_numbers)
