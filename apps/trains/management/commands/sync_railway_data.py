from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.trains.services.live_sync import sync_live_train
from apps.trains.services.train_selection import get_relevant_train_numbers


class Command(BaseCommand):
    help = "Synchronize live status for yesterday and today, sequentially."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            dest="service_date",
            help="Latest service date in YYYY-MM-DD format; its previous day is also synced.",
        )

    def handle(self, *args, **options):
        latest_date = self._service_date(options.get("service_date"))
        service_dates = [latest_date - timedelta(days=1), latest_date]
        total_successful = total_failed = total_skipped = 0

        for service_date in service_dates:
            successful, failed, skipped = self._sync_service_date(service_date)
            total_successful += successful
            total_failed += failed
            total_skipped += skipped

        self.stdout.write(
            self.style.SUCCESS(
                "Sync complete. "
                f"Successful: {total_successful}; skipped: {total_skipped}; "
                f"failed: {total_failed}; "
                f"dates: {service_dates[0]} and {service_dates[1]}."
            )
        )

    def _sync_service_date(self, service_date):
        train_numbers = get_relevant_train_numbers(service_date, max_per_section=30)
        self.stdout.write(
            f"\n{service_date}: selected {len(train_numbers)} unique trains from active sections."
        )

        successful = failed = skipped = 0
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

            if result.get("skipped") == "UNKNOWN_LIVE_STATUS":
                skipped += 1
                self.stdout.write("  - Skipped: live delay/status unavailable")
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
            self.style.SUCCESS(
                f"{service_date} complete. Successful: {successful}; "
                f"skipped: {skipped}; failed: {failed}."
            )
        )
        return successful, failed, skipped

    @staticmethod
    def _service_date(value):
        if not value:
            return timezone.localdate()
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise CommandError("--date must use YYYY-MM-DD format.") from exc
