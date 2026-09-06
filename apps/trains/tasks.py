from datetime import date

from celery import shared_task
from django.utils import timezone

from apps.corridors.models import RailwaySection
from apps.trains.services.live_sync import sync_live_train
from apps.trains.services.railkit import RailKitError
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

    If RailKit has no data for the train on the given date,
    skip the train without retrying.
    """

    service_date_obj = date.fromisoformat(service_date)

    try:
        return sync_live_train(
            train_number=train_number,
            service_date=service_date_obj,
        )

    except RailKitError as exc:

        # Expected case:
        # RailKit has no data for this train on this date.
        #
        # Do NOT retry and do NOT mark the Celery task as failed.
        if (
            exc.status_code == 400
            and "Train data not available for date" in str(exc)
        ):
            return {
                "status": "SKIPPED",
                "train_number": train_number,
                "service_date": service_date,
                "reason": "TRAIN_DATA_NOT_AVAILABLE",
            }

        # Any other RailKit error should still be treated
        # as a real failure.
        raise


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
        max_per_section=30,
    )

    # Global API quota protection.
    # Never queue more than 30 trains per sync cycle.
    train_numbers = train_numbers[:30]

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