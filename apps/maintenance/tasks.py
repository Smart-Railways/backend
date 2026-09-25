import logging
from celery import shared_task
from django.utils import timezone

from .models import MaintenanceLog, MaintenanceTask

logger = logging.getLogger(__name__)


@shared_task
def update_expired_maintenance_tasks():
    """
    Periodic task executed daily at midnight (Asia/Kolkata):
    Checks if a maintenance task's deadline (due_date) has passed (< today).
    If it is not ACTIVE, COMPLETED, or CANCELLED, automatically marks its
    status as DELAYED and sets is_overdue to True. Active work remains active
    until a user explicitly completes or cancels it.
    """
    today = timezone.localdate()

    overdue_tasks = (
        MaintenanceTask.objects
        .filter(due_date__lt=today, is_overdue=False)
        .exclude(
            status__in=[
                MaintenanceTask.Status.COMPLETED,
                MaintenanceTask.Status.CANCELLED,
                MaintenanceTask.Status.DELAYED,
                MaintenanceTask.Status.ACTIVE,
            ]
        )
    )

    updated_count = 0
    for maintenance_task in overdue_tasks:
        maintenance_task.status = MaintenanceTask.Status.DELAYED
        maintenance_task.is_overdue = True
        maintenance_task.save()
        MaintenanceLog.objects.create(
            task=maintenance_task,
            task_code=maintenance_task.task_id,
            event=MaintenanceLog.Event.DELAYED,
            status=maintenance_task.status,
        )
        updated_count += 1

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
