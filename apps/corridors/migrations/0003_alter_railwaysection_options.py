from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('corridors', '0002_railwaysection_destination_station_code_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='railwaysection',
            options={'ordering': ['id']},
        ),
    ]
