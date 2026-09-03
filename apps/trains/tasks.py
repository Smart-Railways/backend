from datetime import date

from celery import shared_task

from apps.corridors.models import RailwaySection
from apps.trains.services.live_sync import sync_live_train
from apps.trains.services.timetable_sync import sync_timetable_for_section
from apps.trains.services.train_selection import get_relevant_train_numbers

@shared_task
def sync_live_train_task(
    train_number: str,
    service_date: str,
):
    """
    Fetch live status for one train and update
    its TrainMovement records.
    """

    service_date_obj = date.fromisoformat(service_date)

    return sync_live_train(
        train_number=train_number,
        service_date=service_date_obj,
    )


@shared_task
def sync_all_timetables():
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
    Select relevant trains and queue individual live-sync tasks.
    """

    if service_date:
        service_date_obj = date.fromisoformat(service_date)
    else:
        service_date_obj = date.today()

    train_numbers = get_relevant_train_numbers(
        service_date=service_date_obj,
        max_per_section=40,
    )

    # Global API quota protection
    train_numbers = train_numbers[:40]

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