from django.contrib import admin
from .models import MandiDailyData


@admin.register(MandiDailyData)
class MandiDailyDataAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "total_cities", "total_records", "created_at", "updated_at")
    list_filter = ("date",)
    search_fields = ("date",)
    readonly_fields = ("date", "data", "created_at", "updated_at")
    ordering = ("-date",)

    def total_cities(self, obj):
        try:
            data = obj.data
            if isinstance(data, dict):
                return len(data.get("data", []))
            return len(data) if isinstance(data, list) else 0
        except Exception:
            return 0
    total_cities.short_description = "Cities"

    def total_records(self, obj):
        try:
            data = obj.data
            if isinstance(data, dict):
                return data.get("total_records", "-")
            return 0
        except Exception:
            return 0
    total_records.short_description = "Total Records"

    def has_add_permission(self, request):
        return False
