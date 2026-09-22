from decimal import Decimal
from django.conf import settings

from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models



# ==========================================================
# SHARED VALIDATORS
# ==========================================================

percentage_validators = [
    MinValueValidator(Decimal("0")),
    MaxValueValidator(Decimal("100")),
]

hex_color_validator = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Enter a valid 6-digit hex color, for example #2E9E33.",
)


# ==========================================================
# MAIN PROJECT DASHBOARD
# ==========================================================
class DashboardBaseModel(models.Model):
    """
    Local base model for project_dashboard only.

    Keeps the same audit fields required by this app
    without depending on the common app.
    """

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        abstract = True

class ProjectDashboard(DashboardBaseModel):
    """
    Main dashboard configuration.

    One record represents one project dashboard, for example:
        AGRI ONE-OS / K2P

    Child records hold:
        - phases
        - project parts
        - KPIs
        - weekly progress
        - highlights/upcoming items
        - risks
        - snapshot KPIs
        - stakeholder actions
    """

    class OverallMode(models.TextChoices):
        WEEKLY = "weekly", "Latest Weekly Progress"
        PARTS = "parts", "Weighted Parts Progress"
        MANUAL = "manual", "Manual"

    class PartsMode(models.TextChoices):
        KPIS = "kpis", "Calculate From KPIs"
        MANUAL = "manual", "Manual"

    class AutoManualMode(models.TextChoices):
        AUTO = "auto", "Automatic"
        MANUAL = "manual", "Manual"

    class PlanMode(models.TextChoices):
        MANUAL = "manual", "Manual"
        LINEAR = "linear", "Linear"

    class HealthStatus(models.TextChoices):
        GOOD = "GOOD", "Good / On Track"
        WATCH = "WATCH", "Watch / Minor Slippage"
        AT_RISK = "AT_RISK", "At Risk / Action Required"

    project_code = models.SlugField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique project identifier, e.g. k2p.",
    )

    project_name = models.CharField(
        max_length=200,
    )

    project_subtitle = models.CharField(
        max_length=300,
        blank=True,
        default="",
    )

    # ------------------------------------------------------
    # HEADER
    # ------------------------------------------------------

    eyebrow = models.CharField(
        max_length=200,
        blank=True,
        default="",
    )

    dashboard_title = models.CharField(
        max_length=200,
        default="LIVE PROJECT DASHBOARD",
    )

    dashboard_subtitle = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )

    reporting_pm_name = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    reporting_pm_role = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    # ------------------------------------------------------
    # PROJECT DATES
    # ------------------------------------------------------

    start_date = models.DateField(
        null=True,
        blank=True,
    )

    end_date = models.DateField(
        null=True,
        blank=True,
    )

    as_of_date = models.DateField(
        null=True,
        blank=True,
        help_text=(
            "Date used for dashboard calculations. "
            "Can later be automatically set to the current date."
        ),
    )

    # ------------------------------------------------------
    # OVERALL PROGRESS
    # ------------------------------------------------------

    overall_progress = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        validators=percentage_validators,
        help_text=(
            "Used when overall progress mode is manual. "
            "Otherwise calculated by the backend."
        ),
    )

    overall_caption = models.CharField(
        max_length=100,
        default="Completed",
    )

    overall_mode = models.CharField(
        max_length=20,
        choices=OverallMode.choices,
        default=OverallMode.WEEKLY,
    )

    # ------------------------------------------------------
    # PART PROGRESS
    # ------------------------------------------------------

    parts_mode = models.CharField(
        max_length=20,
        choices=PartsMode.choices,
        default=PartsMode.KPIS,
    )

    # ------------------------------------------------------
    # WEEKLY TABLE CALCULATION MODES
    # ------------------------------------------------------

    variance_mode = models.CharField(
        max_length=20,
        choices=AutoManualMode.choices,
        default=AutoManualMode.AUTO,
    )

    status_mode = models.CharField(
        max_length=20,
        choices=AutoManualMode.choices,
        default=AutoManualMode.AUTO,
    )

    plan_mode = models.CharField(
        max_length=20,
        choices=PlanMode.choices,
        default=PlanMode.MANUAL,
    )

    periods_mode = models.CharField(
        max_length=20,
        choices=AutoManualMode.choices,
        default=AutoManualMode.MANUAL,
    )

    # ------------------------------------------------------
    # TIMELINE / AUTOMATION
    # ------------------------------------------------------

    calculation_enabled = models.BooleanField(
        default=True,
    )

    nodes_mode = models.CharField(
        max_length=20,
        choices=AutoManualMode.choices,
        default=AutoManualMode.AUTO,
    )

    planned_window = models.PositiveSmallIntegerField(
        default=5,
        help_text=(
            "Number of future weeks shown as planned "
            "after the current week."
        ),
    )

    snapshot_mode = models.CharField(
        max_length=20,
        choices=AutoManualMode.choices,
        default=AutoManualMode.AUTO,
    )

    health_mode = models.CharField(
        max_length=20,
        choices=AutoManualMode.choices,
        default=AutoManualMode.AUTO,
    )

    days_mode = models.CharField(
        max_length=20,
        choices=AutoManualMode.choices,
        default=AutoManualMode.AUTO,
    )

    duration_mode = models.CharField(
        max_length=20,
        choices=AutoManualMode.choices,
        default=AutoManualMode.AUTO,
    )

    current_week_mode = models.CharField(
        max_length=20,
        choices=AutoManualMode.choices,
        default=AutoManualMode.AUTO,
    )

    titles_mode = models.CharField(
        max_length=20,
        choices=AutoManualMode.choices,
        default=AutoManualMode.AUTO,
    )

    # ------------------------------------------------------
    # MANUAL HEALTH FALLBACK
    # ------------------------------------------------------

    manual_health_status = models.CharField(
        max_length=20,
        choices=HealthStatus.choices,
        default=HealthStatus.GOOD,
    )

    manual_health_subtitle = models.CharField(
        max_length=100,
        default="On Track",
    )

    # ------------------------------------------------------
    # UI CONFIGURATION
    #
    # These fields preserve editable presentation content from
    # the existing dashboard without turning purely visual data
    # into unnecessary relational database tables.
    # ------------------------------------------------------

    brand_config = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Dashboard branding such as product/company names."
        ),
    )

    section_titles = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Editable section headings used by the frontend."
        ),
    )

    legend_config = models.JSONField(
        default=list,
        blank=True,
    )

    footer_config = models.JSONField(
        default=list,
        blank=True,
    )

    stakeholder_headers = models.JSONField(
        default=list,
        blank=True,
    )

    # Used only if timeline nodes are manually controlled.
    manual_nodes = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Optional manual timeline node states."
        ),
    )

    # Allows manual values for computed dashboard stat cards
    # without adding many presentation-only DB columns.
    stat_overrides = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Optional manual overrides for duration, current week, "
            "health, overall progress and day statistics."
        ),
    )

    class Meta:
        ordering = [
            "project_name",
        ]
        verbose_name = "Project Dashboard"
        verbose_name_plural = "Project Dashboards"

    def __str__(self):
        return f"{self.project_name} ({self.project_code})"


# ==========================================================
# EXECUTION TIMELINE PHASES
# ==========================================================

class DashboardPhase(DashboardBaseModel):
    dashboard = models.ForeignKey(
        ProjectDashboard,
        on_delete=models.CASCADE,
        related_name="phases",
    )

    name = models.CharField(
        max_length=150,
    )

    span_weeks = models.PositiveSmallIntegerField(
        default=1,
    )

    display_order = models.PositiveSmallIntegerField(
        default=0,
        db_index=True,
    )

    class Meta:
        ordering = [
            "display_order",
            "id",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "dashboard",
                    "display_order",
                ],
                name="unique_dashboard_phase_order",
            ),
        ]

    def __str__(self):
        return f"{self.dashboard.project_code} - {self.name}"


# ==========================================================
# PROJECT PARTS
# ==========================================================

class DashboardPart(DashboardBaseModel):
    class Status(models.TextChoices):
        ON_TRACK = "ON_TRACK", "On Track"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        WATCH = "WATCH", "Watch"
        AT_RISK = "AT_RISK", "At Risk"

    dashboard = models.ForeignKey(
        ProjectDashboard,
        on_delete=models.CASCADE,
        related_name="parts",
    )

    number = models.PositiveSmallIntegerField()

    name = models.CharField(
        max_length=200,
    )

    icon = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    progress = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        validators=percentage_validators,
        help_text=(
            "Manual/fallback progress. "
            "When parts_mode='kpis', backend can calculate this."
        ),
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ON_TRACK,
    )

    color = models.CharField(
        max_length=7,
        default="#2E9E33",
        validators=[
            hex_color_validator,
        ],
    )

    weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("1"),
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
        help_text=(
            "Weight used when overall progress is calculated "
            "from project parts."
        ),
    )

    display_order = models.PositiveSmallIntegerField(
        default=0,
        db_index=True,
    )

    class Meta:
        ordering = [
            "display_order",
            "number",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "dashboard",
                    "number",
                ],
                name="unique_dashboard_part_number",
            ),
            models.UniqueConstraint(
                fields=[
                    "dashboard",
                    "display_order",
                ],
                name="unique_dashboard_part_order",
            ),
        ]

    def __str__(self):
        return (
            f"{self.dashboard.project_code} - "
            f"Part {self.number}: {self.name}"
        )


# ==========================================================
# PART KPIs
# ==========================================================

class DashboardPartKPI(DashboardBaseModel):
    part = models.ForeignKey(
        DashboardPart,
        on_delete=models.CASCADE,
        related_name="kpis",
    )

    label = models.CharField(
        max_length=150,
    )

    actual_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
    )

    target_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
    )

    unit = models.CharField(
        max_length=30,
        blank=True,
        default="",
        help_text=(
            "Examples: %, users, farmers, modules, PKR."
        ),
    )

    compact_numbers = models.BooleanField(
        default=False,
        help_text=(
            "If enabled, values can be displayed as "
            "125K, 8.6M, etc."
        ),
    )

    include_in_progress = models.BooleanField(
        default=True,
        help_text=(
            "Whether this KPI should participate in automatic "
            "part-progress calculation when it has a measurable ratio."
        ),
    )

    display_order = models.PositiveSmallIntegerField(
        default=0,
        db_index=True,
    )

    class Meta:
        ordering = [
            "display_order",
            "id",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "part",
                    "display_order",
                ],
                name="unique_part_kpi_order",
            ),
        ]

    def __str__(self):
        return f"{self.part.name} - {self.label}"


# ==========================================================
# WEEKLY PROGRESS
# ==========================================================

class DashboardWeeklyProgress(DashboardBaseModel):
    class Status(models.TextChoices):
        DONE = "done", "Completed"
        WAIT = "wait", "Waiting"
        IN_PROGRESS = "progress", "In Progress"

    dashboard = models.ForeignKey(
        ProjectDashboard,
        on_delete=models.CASCADE,
        related_name="weekly_progress",
    )

    week_number = models.PositiveSmallIntegerField()

    period_start = models.DateField(
        null=True,
        blank=True,
    )

    period_end = models.DateField(
        null=True,
        blank=True,
    )

    manual_period_label = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text=(
            "Used when periods_mode is manual."
        ),
    )

    planned_progress = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=percentage_validators,
    )

    actual_progress = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=percentage_validators,
    )

    manual_variance = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "Used only when variance_mode is manual."
        ),
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.WAIT,
        help_text=(
            "Used directly in manual mode. "
            "In auto mode backend derives the status."
        ),
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    class Meta:
        ordering = [
            "week_number",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "dashboard",
                    "week_number",
                ],
                name="unique_dashboard_week_number",
            ),
        ]

    def __str__(self):
        return (
            f"{self.dashboard.project_code} - "
            f"Week {self.week_number}"
        )


# ==========================================================
# HIGHLIGHTS / UPCOMING ITEMS
# ==========================================================

class DashboardUpdateItem(DashboardBaseModel):
    class ItemType(models.TextChoices):
        HIGHLIGHT = "HIGHLIGHT", "Highlight"
        UPCOMING = "UPCOMING", "Upcoming"

    dashboard = models.ForeignKey(
        ProjectDashboard,
        on_delete=models.CASCADE,
        related_name="update_items",
    )

    item_type = models.CharField(
        max_length=20,
        choices=ItemType.choices,
        db_index=True,
    )

    text = models.TextField()

    display_order = models.PositiveSmallIntegerField(
        default=0,
        db_index=True,
    )

    class Meta:
        ordering = [
            "item_type",
            "display_order",
            "id",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "dashboard",
                    "item_type",
                    "display_order",
                ],
                name="unique_dashboard_update_item_order",
            ),
        ]

    def __str__(self):
        return (
            f"{self.dashboard.project_code} - "
            f"{self.get_item_type_display()}"
        )


# ==========================================================
# RISK / ISSUE SUMMARY CARDS
# ==========================================================

class DashboardRiskSummary(DashboardBaseModel):
    dashboard = models.ForeignKey(
        ProjectDashboard,
        on_delete=models.CASCADE,
        related_name="risk_summaries",
    )

    key = models.SlugField(
        max_length=50,
    )

    icon = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    label = models.CharField(
        max_length=100,
    )

    value = models.PositiveIntegerField(
        default=0,
    )

    sub_text = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    color = models.CharField(
        max_length=7,
        default="#2E9E33",
        validators=[
            hex_color_validator,
        ],
    )

    display_order = models.PositiveSmallIntegerField(
        default=0,
        db_index=True,
    )

    class Meta:
        ordering = [
            "display_order",
            "id",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "dashboard",
                    "key",
                ],
                name="unique_dashboard_risk_key",
            ),
            models.UniqueConstraint(
                fields=[
                    "dashboard",
                    "display_order",
                ],
                name="unique_dashboard_risk_order",
            ),
        ]

    def __str__(self):
        return f"{self.dashboard.project_code} - {self.label}"


# ==========================================================
# PROJECT KPI SNAPSHOT
# ==========================================================

class DashboardSnapshotKPI(DashboardBaseModel):
    dashboard = models.ForeignKey(
        ProjectDashboard,
        on_delete=models.CASCADE,
        related_name="snapshot_kpis",
    )

    key = models.SlugField(
        max_length=60,
    )

    icon = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    label = models.CharField(
        max_length=150,
    )

    actual_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0"),
    )

    target_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
    )

    unit = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    compact_numbers = models.BooleanField(
        default=True,
    )

    manual_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=percentage_validators,
        help_text=(
            "Used when snapshot_mode is manual."
        ),
    )

    color = models.CharField(
        max_length=7,
        default="#2E9E33",
        validators=[
            hex_color_validator,
        ],
    )

    display_order = models.PositiveSmallIntegerField(
        default=0,
        db_index=True,
    )

    class Meta:
        ordering = [
            "display_order",
            "id",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "dashboard",
                    "key",
                ],
                name="unique_dashboard_snapshot_key",
            ),
            models.UniqueConstraint(
                fields=[
                    "dashboard",
                    "display_order",
                ],
                name="unique_dashboard_snapshot_order",
            ),
        ]

    def __str__(self):
        return f"{self.dashboard.project_code} - {self.label}"


# ==========================================================
# STAKEHOLDER ACTIONS
# ==========================================================

class DashboardStakeholderAction(DashboardBaseModel):
    class Status(models.TextChoices):
        WAIT = "wait", "Waiting"
        IN_PROGRESS = "progress", "In Progress"
        DONE = "done", "Completed"
        OVERDUE = "overdue", "Overdue"

    dashboard = models.ForeignKey(
        ProjectDashboard,
        on_delete=models.CASCADE,
        related_name="stakeholder_actions",
    )

    stakeholder = models.CharField(
        max_length=200,
    )

    action = models.TextField()

    due_date = models.DateField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.WAIT,
        db_index=True,
    )

    display_order = models.PositiveSmallIntegerField(
        default=0,
        db_index=True,
    )

    class Meta:
        ordering = [
            "display_order",
            "due_date",
            "id",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "dashboard",
                    "display_order",
                ],
                name="unique_dashboard_stakeholder_order",
            ),
        ]

    def __str__(self):
        return (
            f"{self.dashboard.project_code} - "
            f"{self.stakeholder}"
        )