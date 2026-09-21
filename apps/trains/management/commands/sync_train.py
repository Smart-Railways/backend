from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.trains.services.live_sync import sync_live_train


class Command(BaseCommand):
    help = "Synchronize detailed live status for one train."

    def add_arguments(self, parser):
        parser.add_argument("train_number")
        parser.add_argument("--date", dest="service_date", help="Service date in YYYY-MM-DD format.")

    def handle(self, *args, **options):
        service_date = self._service_date(options.get("service_date"))
        result = sync_live_train(options["train_number"], service_date)

        if result.get("error"):
            raise CommandError(result["error"])

        self.stdout.write(f"Train: {result['train_number']}")
        self.stdout.write(f"Name: {result.get('train_name') or 'Unknown'}")
        self.stdout.write(f"Date: {result['service_date']}")
        delay = result.get("delay_minutes")
        self.stdout.write(f"Delay: {delay} minutes" if delay is not None else "Delay: unavailable")
        self.stdout.write(f"Status: {result.get('status_label') or 'Unavailable'}")
        self.stdout.write(f"Movements updated: {len(result['updated_movements'])}")

    @staticmethod
    def _service_date(value):
        if not value:
            return timezone.localdate()
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise CommandError("--date must use YYYY-MM-DD format.") from exc
