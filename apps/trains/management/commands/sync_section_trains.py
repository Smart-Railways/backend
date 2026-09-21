from django.core.management.base import BaseCommand

from apps.corridors.models import RailwaySection
from apps.trains.services.timetable_sync import sync_timetable_for_section


class Command(BaseCommand):
    help = "Discover and synchronize up to 10 trains for each active railway section."

    def handle(self, *args, **options):
        sections = list(RailwaySection.objects.filter(is_active=True).order_by("id"))
        successful = failed = total_selected = 0

        if not sections:
            self.stdout.write("No active railway sections found.")
            return

        for index, section in enumerate(sections, start=1):
            self.stdout.write(
                f"[{index}/{len(sections)}] {section.source_station} -> {section.destination_station}"
            )
            try:
                result = sync_timetable_for_section(section, max_trains=10)
            except Exception as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"  Error: {exc}"))
                continue

            successful += 1
            total_selected += result["trains_selected"]
            self.stdout.write(f"  Found: {result['trains_received']} trains")
            self.stdout.write(f"  Selected: {result['trains_selected']}")
            self.stdout.write(f"  Created trains: {result['trains_created']}")
            self.stdout.write(f"  Updated trains: {result['trains_updated']}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Sync complete. Sections successful: {successful}; failed: {failed}; "
                f"trains selected: {total_selected}."
            )
        )
