from datetime import date

from celery import shared_task
from django.utils import timezone

from apps.corridors.models import RailwaySection
from apps.trains.services.live_sync import sync_live_train
from apps.trains.services.timetable_sync import sync_timetable_for_section
from apps.trains.services.train_selection import get_relevant_train_numbers


@shared_task(
    bind=True,
    rate_limit="15/m",
)
def sync_live_train_task(
    self,
    train_number: str,
    service_date: str,
):
    """
    Fetch live status for one train and update
    its TrainMovement records.

    Service and malformed-response errors are returned by sync_live_train as
    per-train summaries, so a failed request does not affect other tasks.
    """

    service_date_obj = date.fromisoformat(service_date)

    return sync_live_train(
        train_number=train_number,
        service_date=service_date_obj,
    )


@shared_task
def sync_all_timetables():
    """
    Sync timetable data for all active railway sections.
    """

    sections = RailwaySection.objects.filter(
        is_active=True
    )

    results = []

    for section in sections:
        try:
            result = sync_timetable_for_section(section)

            results.append({
                "section": section.name,
                "success": True,
                "result": result,
            })

        except Exception as exc:
            results.append({
                "section": section.name,
                "success": False,
                "error": str(exc),
            })

    return results


@shared_task
def sync_relevant_live_trains(
    service_date: str | None = None,
):
    """
    Select relevant trains that actually run on the given date
    and queue individual live-sync tasks.
    """

    if service_date:
        service_date_obj = date.fromisoformat(service_date)
    else:
        # Use Django's configured timezone (Asia/Kolkata)
        service_date_obj = timezone.localdate()

    train_numbers = get_relevant_train_numbers(
        service_date=service_date_obj,
        max_per_section=10,
    )

    queued = []

    for train_number in train_numbers:

        result = sync_live_train_task.delay(
            train_number,
            service_date_obj.isoformat(),
        )

        queued.append({
            "train_number": train_number,
            "task_id": result.id,
        })

    return {
        "service_date": service_date_obj.isoformat(),
        "trains_selected": len(train_numbers),
        "tasks_queued": len(queued),
        "trains": queued,
    }
