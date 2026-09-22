from django.contrib import admin

from .models import (
    DashboardPart,
    DashboardPartKPI,
    DashboardPhase,
    DashboardRiskSummary,
    DashboardSnapshotKPI,
    DashboardStakeholderAction,
    DashboardUpdateItem,
    DashboardWeeklyProgress,
    ProjectDashboard,
)


# ==========================================================
# SHARED ADMIN MIXIN
# ==========================================================

class AuditAdminMixin:
    """
    Automatically maintain BaseModel audit fields.

    created_by:
        Set only when the record is first created.

    updated_by:
        Updated every time the record is saved through Django Admin.
    """

    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        if not change and not obj.created_by_id:
            obj.created_by = request.user

        obj.updated_by = request.user

        super().save_model(
            request,
            obj,
            form,
            change,
        )


# ==========================================================
# INLINE: PHASES
# ==========================================================

class DashboardPhaseInline(admin.TabularInline):
    model = DashboardPhase
    extra = 0

    fields = (
        "display_order",
        "name",
        "span_weeks",
        "is_active",
    )

    ordering = (
        "display_order",
        "id",
    )


# ==========================================================
# INLINE: PROJECT PARTS
# ==========================================================

class DashboardPartInline(admin.TabularInline):
    model = DashboardPart
    extra = 0

    fields = (
        "display_order",
        "number",
        "name",
        "progress",
        "status",
        "weight",
        "color",
        "is_active",
    )

    ordering = (
        "display_order",
        "number",
    )

    show_change_link = True


# ==========================================================
# INLINE: WEEKLY PROGRESS
# ==========================================================

class DashboardWeeklyProgressInline(admin.TabularInline):
    model = DashboardWeeklyProgress
    extra = 0

    fields = (
        "week_number",
        "period_start",
        "period_end",
        "planned_progress",
        "actual_progress",
        "status",
        "is_active",
    )

    ordering = (
        "week_number",
    )

    show_change_link = True


# ==========================================================
# INLINE: UPDATE ITEMS
# ==========================================================

class DashboardUpdateItemInline(admin.TabularInline):
    model = DashboardUpdateItem
    extra = 0

    fields = (
        "display_order",
        "item_type",
        "text",
        "is_active",
    )

    ordering = (
        "item_type",
        "display_order",
        "id",
    )

    show_change_link = True


# ==========================================================
# INLINE: RISK SUMMARY
# ==========================================================

class DashboardRiskSummaryInline(admin.TabularInline):
    model = DashboardRiskSummary
    extra = 0

    fields = (
        "display_order",
        "key",
        "label",
        "value",
        "sub_text",
        "color",
        "is_active",
    )

    ordering = (
        "display_order",
        "id",
    )

    show_change_link = True


# ==========================================================
# INLINE: SNAPSHOT KPI
# ==========================================================

class DashboardSnapshotKPIInline(admin.TabularInline):
    model = DashboardSnapshotKPI
    extra = 0

    fields = (
        "display_order",
        "key",
        "label",
        "actual_value",
        "target_value",
        "unit",
        "color",
        "is_active",
    )

    ordering = (
        "display_order",
        "id",
    )

    show_change_link = True


# ==========================================================
# INLINE: STAKEHOLDER ACTIONS
# ==========================================================

class DashboardStakeholderActionInline(admin.TabularInline):
    model = DashboardStakeholderAction
    extra = 0

    fields = (
        "display_order",
        "stakeholder",
        "action",
        "due_date",
        "status",
        "is_active",
    )

    ordering = (
        "display_order",
        "due_date",
        "id",
    )

    show_change_link = True


# ==========================================================
# PROJECT DASHBOARD ADMIN
# ==========================================================

@admin.register(ProjectDashboard)
class ProjectDashboardAdmin(
    AuditAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "project_name",
        "project_code",
        "start_date",
        "end_date",
        "as_of_date",
        "overall_mode",
        "overall_progress",
        "is_active",
        "updated_at",
    )

    list_filter = (
        "is_active",
        "overall_mode",
        "parts_mode",
        "health_mode",
        "calculation_enabled",
    )

    search_fields = (
        "project_name",
        "project_code",
        "dashboard_title",
        "reporting_pm_name",
    )

    ordering = (
        "project_name",
    )

    readonly_fields = AuditAdminMixin.readonly_fields

    fieldsets = (
        (
            "Project",
            {
                "fields": (
                    "project_code",
                    "project_name",
                    "project_subtitle",
                    "is_active",
                )
            },
        ),
        (
            "Dashboard Header",
            {
                "fields": (
                    "eyebrow",
                    "dashboard_title",
                    "dashboard_subtitle",
                    "reporting_pm_name",
                    "reporting_pm_role",
                )
            },
        ),
        (
            "Project Dates",
            {
                "fields": (
                    "start_date",
                    "end_date",
                    "as_of_date",
                )
            },
        ),
        (
            "Overall Progress",
            {
                "fields": (
                    "overall_mode",
                    "overall_progress",
                    "overall_caption",
                )
            },
        ),
        (
            "Project Parts",
            {
                "fields": (
                    "parts_mode",
                )
            },
        ),
        (
            "Weekly Progress Configuration",
            {
                "fields": (
                    "plan_mode",
                    "periods_mode",
                    "variance_mode",
                    "status_mode",
                )
            },
        ),
        (
            "Automatic Calculations",
            {
                "fields": (
                    "calculation_enabled",
                    "nodes_mode",
                    "planned_window",
                    "snapshot_mode",
                    "health_mode",
                    "days_mode",
                    "duration_mode",
                    "current_week_mode",
                    "titles_mode",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
        (
            "Manual Health Fallback",
            {
                "fields": (
                    "manual_health_status",
                    "manual_health_subtitle",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
        (
            "Frontend Configuration",
            {
                "fields": (
                    "brand_config",
                    "section_titles",
                    "legend_config",
                    "footer_config",
                    "stakeholder_headers",
                    "manual_nodes",
                    "stat_overrides",
                ),
                "classes": (
                    "collapse",
                ),
                "description": (
                    "These JSON fields preserve presentation-level "
                    "configuration from the existing dashboard."
                ),
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
    )

    inlines = (
        DashboardPhaseInline,
        DashboardPartInline,
        DashboardWeeklyProgressInline,
        DashboardUpdateItemInline,
        DashboardRiskSummaryInline,
        DashboardSnapshotKPIInline,
        DashboardStakeholderActionInline,
    )


# ==========================================================
# PROJECT PART ADMIN
# ==========================================================

class DashboardPartKPIInline(admin.TabularInline):
    model = DashboardPartKPI
    extra = 0

    fields = (
        "display_order",
        "label",
        "actual_value",
        "target_value",
        "unit",
        "include_in_progress",
        "compact_numbers",
        "is_active",
    )

    ordering = (
        "display_order",
        "id",
    )

    show_change_link = True


@admin.register(DashboardPart)
class DashboardPartAdmin(
    AuditAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "name",
        "dashboard",
        "number",
        "progress",
        "status",
        "weight",
        "is_active",
    )

    list_filter = (
        "dashboard",
        "status",
        "is_active",
    )

    search_fields = (
        "name",
        "dashboard__project_name",
        "dashboard__project_code",
    )

    ordering = (
        "dashboard",
        "display_order",
        "number",
    )

    autocomplete_fields = (
        "dashboard",
    )

    readonly_fields = AuditAdminMixin.readonly_fields

    inlines = (
        DashboardPartKPIInline,
    )


# ==========================================================
# PART KPI ADMIN
# ==========================================================

@admin.register(DashboardPartKPI)
class DashboardPartKPIAdmin(
    AuditAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "label",
        "part",
        "actual_value",
        "target_value",
        "unit",
        "include_in_progress",
        "is_active",
    )

    list_filter = (
        "part__dashboard",
        "include_in_progress",
        "is_active",
    )

    search_fields = (
        "label",
        "part__name",
        "part__dashboard__project_name",
    )

    ordering = (
        "part",
        "display_order",
        "id",
    )

    autocomplete_fields = (
        "part",
    )

    readonly_fields = AuditAdminMixin.readonly_fields


# ==========================================================
# PHASE ADMIN
# ==========================================================

@admin.register(DashboardPhase)
class DashboardPhaseAdmin(
    AuditAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "name",
        "dashboard",
        "span_weeks",
        "display_order",
        "is_active",
    )

    list_filter = (
        "dashboard",
        "is_active",
    )

    search_fields = (
        "name",
        "dashboard__project_name",
    )

    ordering = (
        "dashboard",
        "display_order",
        "id",
    )

    autocomplete_fields = (
        "dashboard",
    )

    readonly_fields = AuditAdminMixin.readonly_fields


# ==========================================================
# WEEKLY PROGRESS ADMIN
# ==========================================================

@admin.register(DashboardWeeklyProgress)
class DashboardWeeklyProgressAdmin(
    AuditAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "dashboard",
        "week_number",
        "period_start",
        "period_end",
        "planned_progress",
        "actual_progress",
        "status",
        "is_active",
    )

    list_filter = (
        "dashboard",
        "status",
        "is_active",
    )

    search_fields = (
        "dashboard__project_name",
        "manual_period_label",
        "notes",
    )

    ordering = (
        "dashboard",
        "week_number",
    )

    autocomplete_fields = (
        "dashboard",
    )

    readonly_fields = AuditAdminMixin.readonly_fields


# ==========================================================
# HIGHLIGHTS / UPCOMING ADMIN
# ==========================================================

@admin.register(DashboardUpdateItem)
class DashboardUpdateItemAdmin(
    AuditAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "short_text",
        "dashboard",
        "item_type",
        "display_order",
        "is_active",
    )

    list_filter = (
        "dashboard",
        "item_type",
        "is_active",
    )

    search_fields = (
        "text",
        "dashboard__project_name",
    )

    ordering = (
        "dashboard",
        "item_type",
        "display_order",
        "id",
    )

    autocomplete_fields = (
        "dashboard",
    )

    readonly_fields = AuditAdminMixin.readonly_fields

    @admin.display(
        description="Text",
    )
    def short_text(self, obj):
        if len(obj.text) <= 70:
            return obj.text

        return f"{obj.text[:67]}..."


# ==========================================================
# RISK SUMMARY ADMIN
# ==========================================================

@admin.register(DashboardRiskSummary)
class DashboardRiskSummaryAdmin(
    AuditAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "label",
        "dashboard",
        "key",
        "value",
        "color",
        "display_order",
        "is_active",
    )

    list_filter = (
        "dashboard",
        "is_active",
    )

    search_fields = (
        "label",
        "key",
        "dashboard__project_name",
    )

    ordering = (
        "dashboard",
        "display_order",
        "id",
    )

    autocomplete_fields = (
        "dashboard",
    )

    readonly_fields = AuditAdminMixin.readonly_fields


# ==========================================================
# SNAPSHOT KPI ADMIN
# ==========================================================

@admin.register(DashboardSnapshotKPI)
class DashboardSnapshotKPIAdmin(
    AuditAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "label",
        "dashboard",
        "actual_value",
        "target_value",
        "unit",
        "color",
        "display_order",
        "is_active",
    )

    list_filter = (
        "dashboard",
        "is_active",
    )

    search_fields = (
        "label",
        "key",
        "dashboard__project_name",
    )

    ordering = (
        "dashboard",
        "display_order",
        "id",
    )

    autocomplete_fields = (
        "dashboard",
    )

    readonly_fields = AuditAdminMixin.readonly_fields


# ==========================================================
# STAKEHOLDER ACTION ADMIN
# ==========================================================

@admin.register(DashboardStakeholderAction)
class DashboardStakeholderActionAdmin(
    AuditAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "stakeholder",
        "dashboard",
        "due_date",
        "status",
        "display_order",
        "is_active",
    )

    list_filter = (
        "dashboard",
        "status",
        "is_active",
    )

    search_fields = (
        "stakeholder",
        "action",
        "dashboard__project_name",
    )

    ordering = (
        "dashboard",
        "display_order",
        "due_date",
        "id",
    )

    autocomplete_fields = (
        "dashboard",
    )

    readonly_fields = AuditAdminMixin.readonly_fields
