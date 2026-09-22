from django.db import models
from django.core.exceptions import ValidationError


class CronConfig(models.Model):
    """
    Singleton model — only one row ever exists.
    All cron-related settings live here and are editable from Django admin.
    """

    # DB Backup settings
    backup_interval_days = models.PositiveSmallIntegerField(
        default=2,
        help_text="How many days between automated database backups. Default: 2.",
    )
    backup_keep_count = models.PositiveSmallIntegerField(
        default=10,
        help_text="How many backup files to keep before rotating old ones.",
    )
    last_backup_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Set automatically when a backup runs. Do not edit.",
    )

    # Mandi settings
    mandi_fetch_hour = models.PositiveSmallIntegerField(
        default=11,
        help_text="Hour (24h, PKT) at which mandi rates are fetched daily. Default: 11.",
    )
    mandi_department = models.CharField(
        max_length=50,
        default="LIMS",
        help_text="Department code passed to the AMIS API.",
    )

    class Meta:
        verbose_name = "Cron Configuration"
        verbose_name_plural = "Cron Configuration"

    def __str__(self):
        return "Cron Configuration"

    def clean(self):
        if self.mandi_fetch_hour > 23:
            raise ValidationError({"mandi_fetch_hour": "Hour must be 0-23."})

    def save(self, *args, **kwargs):
        # Enforce singleton — always save as pk=1
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # Prevent deletion from admin

    @classmethod
    def get(cls):
        """Always returns the singleton, creating it if needed."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
