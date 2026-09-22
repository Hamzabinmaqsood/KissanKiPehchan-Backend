from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CronConfig",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("backup_interval_days", models.PositiveSmallIntegerField(default=2, help_text="How many days between automated database backups.")),
                ("backup_keep_count", models.PositiveSmallIntegerField(default=10, help_text="How many backup files to keep before rotating old ones.")),
                ("last_backup_at", models.DateTimeField(blank=True, null=True, help_text="Set automatically when a backup runs. Do not edit.")),
                ("mandi_fetch_hour", models.PositiveSmallIntegerField(default=11, help_text="Hour (24h PKT) at which mandi rates are fetched daily.")),
                ("mandi_department", models.CharField(default="LIMS", max_length=50, help_text="Department code passed to the AMIS API.")),
            ],
            options={"verbose_name": "Cron Configuration", "verbose_name_plural": "Cron Configuration"},
        ),
    ]
