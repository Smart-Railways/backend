from datetime import date

from celery import shared_task

from apps.corridors.models import RailwaySection
from apps.trains.services.live_sync import sync_live_train
from apps.trains.services.timetable_sync import sync_timetable_for_section


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