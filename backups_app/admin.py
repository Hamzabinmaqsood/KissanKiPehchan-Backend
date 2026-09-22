from django.contrib import admin
from .models import CronConfig


@admin.register(CronConfig)
class CronConfigAdmin(admin.ModelAdmin):
    """
    Singleton admin — shows the single config row directly.
    Hides the list view and goes straight to the edit form.
    """

    fieldsets = (
        (
            "Database Backup",
            {
                "fields": (
                    "backup_interval_days",
                    "backup_keep_count",
                    "last_backup_at",
                ),
                "description": (
                    "The backup command runs daily via crontab. "
                    "It only creates a new backup when backup_interval_days "
                    "have elapsed since the last one."
                ),
            },
        ),
        (
            "Mandi Rates",
            {
                "fields": (
                    "mandi_fetch_hour",
                    "mandi_department",
                ),
                "description": (
                    "Mandi rates are fetched once daily by a cron job. "
                    "Update mandi_fetch_hour and redeploy the server crontab "
                    "if you change the fetch time."
                ),
            },
        ),
    )

    readonly_fields = ("last_backup_at",)

    def has_add_permission(self, request):
        # Prevent creating a second row
        return not CronConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Redirect list → edit the singleton directly
        from django.shortcuts import redirect
        obj = CronConfig.get()
        return redirect(f"/api/admin/backups_app/cronconfig/{obj.pk}/change/")
