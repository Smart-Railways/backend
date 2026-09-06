import logging
from celery import shared_task
from django.utils import timezone

from .models import MaintenanceTask

logger = logging.getLogger(__name__)


@shared_task
def update_expired_maintenance_tasks():
    """
    Periodic task executed daily at midnight (Asia/Kolkata):
    Checks if a maintenance task's deadline (due_date) has passed (< today).
    If it has not been COMPLETED or CANCELLED, automatically marks its status
    as DELAYED and sets is_overdue to True.
    """
    today = timezone.localdate()

    updated_count = (
        MaintenanceTask.objects
        .filter(due_date__lt=today)
        .exclude(
            status__in=[
                MaintenanceTask.Status.COMPLETED,
                MaintenanceTask.Status.CANCELLED,
                MaintenanceTask.Status.DELAYED,
            ]
        )
        .update(
            status=MaintenanceTask.Status.DELAYED,
            is_overdue=True,
        )
    )

    logger.info(
        "Updated %d expired maintenance task(s) to DELAYED on %s.",
        updated_count,
        today,
    )

    return {
        "status": "SUCCESS",
        "date": str(today),
        "updated_tasks_count": updated_count,
    }
