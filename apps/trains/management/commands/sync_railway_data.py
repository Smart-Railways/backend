from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.trains.services.live_sync import sync_live_train
from apps.trains.services.train_selection import get_relevant_train_numbers


class Command(BaseCommand):
    help = "Synchronize live status sequentially for selected section trains."

    def add_arguments(self, parser):
        parser.add_argument("--date", dest="service_date", help="Service date in YYYY-MM-DD format.")

    def handle(self, *args, **options):
        service_date = self._service_date(options.get("service_date"))
        train_numbers = get_relevant_train_numbers(service_date, max_per_section=10)
        self.stdout.write(
            f"Selected {len(train_numbers)} unique trains from active sections for {service_date}."
        )

        successful = failed = 0
        for index, train_number in enumerate(train_numbers, start=1):
            self.stdout.write(f"[{index}/{len(train_numbers)}] {train_number}")
            try:
                result = sync_live_train(train_number, service_date)
                if result.get("error"):
                    raise RuntimeError(result["error"])
            except Exception as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"  x {exc}"))
                continue

            successful += 1
            delay = result.get("delay_minutes")
            live_label = result.get("status_label")
            detail = live_label or (
                f"{delay} min delay" if delay is not None else "Delay unavailable"
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"  OK {detail} | {len(result['updated_movements'])} movements updated"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(f"Sync complete. Successful: {successful}; failed: {failed}.")
        )

    @staticmethod
    def _service_date(value):
        if not value:
            return timezone.localdate()
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise CommandError("--date must use YYYY-MM-DD format.") from exc
