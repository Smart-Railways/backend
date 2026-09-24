from django.db import migrations


# Consecutive operational sections on the New Delhi--Howrah main corridor.
# Distances are route kilometres and are kept with the section so block-window
# planning and schedule matching can operate on each leg independently.
NEW_DELHI_HOWRAH_SECTIONS = (
    ("New Delhi–Howrah Main Corridor: New Delhi–Kanpur Central", "New Delhi", "NDLS", "Kanpur Central", "CNB", 440.0),
    ("New Delhi–Howrah Main Corridor: Kanpur Central–Prayagraj Junction", "Kanpur Central", "CNB", "Prayagraj Junction", "PRYJ", 194.0),
    ("New Delhi–Howrah Main Corridor: Prayagraj Junction–Pt. Deen Dayal Upadhyaya Junction", "Prayagraj Junction", "PRYJ", "Pt. Deen Dayal Upadhyaya Junction", "DDU", 152.0),
    ("New Delhi–Howrah Main Corridor: Pt. Deen Dayal Upadhyaya Junction–Gaya Junction", "Pt. Deen Dayal Upadhyaya Junction", "DDU", "Gaya Junction", "GAYA", 203.0),
    ("New Delhi–Howrah Main Corridor: Gaya Junction–Dhanbad Junction", "Gaya Junction", "GAYA", "Dhanbad Junction", "DHN", 203.0),
    ("New Delhi–Howrah Main Corridor: Dhanbad Junction–Asansol Junction", "Dhanbad Junction", "DHN", "Asansol Junction", "ASN", 58.0),
    ("New Delhi–Howrah Main Corridor: Asansol Junction–Howrah Junction", "Asansol Junction", "ASN", "Howrah Junction", "HWH", 200.0),
)


def add_sections(apps, schema_editor):
    RailwaySection = apps.get_model("corridors", "RailwaySection")
    for name, source, source_code, destination, destination_code, distance in NEW_DELHI_HOWRAH_SECTIONS:
        RailwaySection.objects.get_or_create(
            name=name,
            defaults={
                "source_station": source,
                "source_station_code": source_code,
                "destination_station": destination,
                "destination_station_code": destination_code,
                "distance_km": distance,
                "is_active": True,
            },
        )


def remove_sections(apps, schema_editor):
    RailwaySection = apps.get_model("corridors", "RailwaySection")
    RailwaySection.objects.filter(
        name__startswith="New Delhi–Howrah Main Corridor:"
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("corridors", "0003_alter_railwaysection_options"),
    ]

    operations = [
        migrations.RunPython(add_sections, remove_sections),
    ]
