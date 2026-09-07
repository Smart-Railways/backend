import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blocks', '0002_blockwindow_task'),
        ('maintenance', '0002_alter_maintenancetask_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='blockwindow',
            name='task',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='block_windows',
                to='maintenance.maintenancetask',
            ),
        ),
    ]
