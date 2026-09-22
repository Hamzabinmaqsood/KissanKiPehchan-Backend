from __future__ import annotations

import math
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

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
# DEFAULT PRESENTATION CONFIGURATION
# ==========================================================

DEFAULT_BRAND = {
    "productName": "AgriOne-OS",
    "productSub": "(K2P)",
    "companyA": "SYNTEC",
    "companyB": "X",
    "companyTag": "Simplifying Technology",
}


DEFAULT_SECTION_TITLES = {
    "partsTitle": "5 PARTS PROGRESS & KPI SUMMARY",
    "overallTitle": "OVERALL PROJECT PROGRESS",
    "timelineTitle": "EXECUTION TIMELINE",
    "highlightsTitle": "KEY HIGHLIGHTS (THIS WEEK)",
    "upcomingTitle": "UPCOMING NEXT WEEK",
    "weeklyTitle": "WEEKLY PROGRESS OVERVIEW",
    "riskTitle": "RISK & ISSUE SUMMARY",
    "snapTitle": "PROJECT KPI SNAPSHOT (CUMULATIVE)",
    "stakeTitle": "STAKEHOLDER ACTIONS & DEADLINES",
}


DEFAULT_LEGEND = [
    {
        "l": "Completed",
        "c": "#2E9E33",
    },
    {
        "l": "In Progress",
        "c": "#1976D2",
    },
    {
        "l": "Planned",
        "c": "#C9CDD3",
    },
    {
        "l": "Pending",
        "c": "#DFE3E8",
    },
]


DEFAULT_STAKEHOLDER_HEADERS = [
    "STAKEHOLDER",
    "ACTION REQUIRED",
    "DUE DATE",
    "STATUS",
]


PART_STATUS_MAP = {
    "on track": DashboardPart.Status.ON_TRACK,
    "in progress": DashboardPart.Status.IN_PROGRESS,
    "watch": DashboardPart.Status.WATCH,
    "at risk": DashboardPart.Status.AT_RISK,
}


# ==========================================================
# GENERAL HELPERS
# ==========================================================

def _decimal(value, default=None):
    if value is None:
        return default

    if isinstance(value, Decimal):
        return value

    if isinstance(value, (int, float)):
        return Decimal(str(value))

    text = str(value).strip()

    if not text or text == "-":
        return default

    text = text.replace(",", "")
    text = text.replace("%", "")
    text = re.sub(
        r"(?i)\bPKR\b",
        "",
        text,
    )
    text = re.sub(
        r"(?i)\bRs\.?\b",
        "",
        text,
    )
    text = text.strip()

    multiplier = Decimal("1")

    if text and text[-1:].lower() in {
        "k",
        "m",
        "b",
    }:
        suffix = text[-1:].lower()
        text = text[:-1].strip()

        if suffix == "k":
            multiplier = Decimal("1000")
        elif suffix == "m":
            multiplier = Decimal("1000000")
        elif suffix == "b":
            multiplier = Decimal("1000000000")

    try:
        return Decimal(text) * multiplier
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ):
        return default


def _integer(value, default=0):
    parsed = _decimal(
        value,
        default=None,
    )

    if parsed is None:
        return default

    return int(parsed)


def _round_percentage(value):
    if value is None:
        return 0

    return int(
        Decimal(str(value)).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )


def _clamp_percentage(value):
    value = Decimal(str(value or 0))

    if value < 0:
        return Decimal("0")

    if value > 100:
        return Decimal("100")

    return value


def _clean_decimal(value):
    if value is None:
        return None

    value = Decimal(str(value))

    if value == value.to_integral():
        return int(value)

    return float(
        value.normalize()
    )


def _format_number(
    value,
    *,
    compact=False,
):
    if value is None:
        return "-"

    value = Decimal(str(value))

    negative = value < 0
    absolute = abs(value)

    if compact:
        thresholds = (
            (
                Decimal("1000000000"),
                "B",
            ),
            (
                Decimal("1000000"),
                "M",
            ),
            (
                Decimal("1000"),
                "K",
            ),
        )

        for threshold, suffix in thresholds:
            if absolute >= threshold:
                result = (
                    absolute / threshold
                ).quantize(
                    Decimal("0.1"),
                    rounding=ROUND_HALF_UP,
                )

                text = format(
                    result,
                    "f",
                ).rstrip("0").rstrip(".")

                if negative:
                    text = f"-{text}"

                return f"{text}{suffix}"

    if value == value.to_integral():
        return f"{int(value):,}"

    text = format(
        value.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        ),
        "f",
    ).rstrip("0").rstrip(".")

    return text


def _format_percentage(value):
    if value is None:
        return "-"

    value = Decimal(str(value))

    if value == value.to_integral():
        return f"{int(value)}%"

    value = value.quantize(
        Decimal("0.1"),
        rounding=ROUND_HALF_UP,
    )

    return (
        f"{format(value, 'f').rstrip('0').rstrip('.')}%"
    )


def _format_variance(value):
    if value is None:
        return "-"

    value = Decimal(str(value))

    text = _format_percentage(
        abs(value)
    )

    if value > 0:
        return f"+{text}"

    if value < 0:
        return f"-{text}"

    return "0%"


def _date_from_value(value):
    if not value:
        return None

    if isinstance(value, date):
        return value

    text = str(value).strip()

    if not text:
        return None

    # ISO
    try:
        return date.fromisoformat(
            text
        )
    except ValueError:
        pass

    # Remove 1st / 2nd / 3rd / 4th
    text = re.sub(
        r"(\d+)(st|nd|rd|th)",
        r"\1",
        text,
        flags=re.IGNORECASE,
    )

    for fmt in (
        "%d %b %Y",
        "%d %B %Y",
        "%d %b",
        "%d %B",
    ):
        try:
            parsed = datetime.strptime(
                text,
                fmt,
            )

            if "%Y" not in fmt:
                parsed = parsed.replace(
                    year=timezone.localdate().year
                )

            return parsed.date()
        except ValueError:
            continue

    return None


def _format_date(value):
    if not value:
        return ""

    return (
        f"{value.day} "
        f"{value.strftime('%b %Y')}"
    )


def _format_short_date(value):
    if not value:
        return ""

    return (
        f"{value.day} "
        f"{value.strftime('%b')}"
    )


def _format_date_range(
    start,
    end,
    *,
    include_year=False,
):
    if not start or not end:
        return ""

    if start.month == end.month:
        result = (
            f"{start.day} – "
            f"{end.day} "
            f"{end.strftime('%b')}"
        )
    else:
        result = (
            f"{start.day} "
            f"{start.strftime('%b')} – "
            f"{end.day} "
            f"{end.strftime('%b')}"
        )

    if include_year:
        result = (
            f"{result} {end.year}"
        )

    return result


def _display_time(value):
    if not value:
        return ""

    local_value = timezone.localtime(
        value
    )

    return local_value.strftime(
        "%I:%M %p"
    ).lstrip("0")


def _display_updated_date(value):
    if not value:
        return ""

    local_value = timezone.localtime(
        value
    )

    return (
        f"{local_value.day} "
        f"{local_value.strftime('%b %Y')}"
    )


def _audit_kwargs(user):
    if not user:
        return {}

    return {
        "created_by": user,
        "updated_by": user,
    }


# ==========================================================
# KPI PARSING / DISPLAY
# ==========================================================

def _parse_kpi_display_value(value):
    """
    Converts the dashboard's existing free-text KPI format into
    structured values.

    Examples:
        36 / 58
        78%
        125K
        8,450
    """

    text = str(
        value or ""
    ).strip()

    if not text:
        return {
            "actual": None,
            "target": None,
            "unit": "",
            "compact": False,
        }

    if "/" in text:
        left, right = text.split(
            "/",
            1,
        )

        return {
            "actual": _decimal(left),
            "target": _decimal(right),
            "unit": (
                "%"
                if "%" in text
                else ""
            ),
            "compact": bool(
                re.search(
                    r"[KMB]",
                    text,
                    flags=re.IGNORECASE,
                )
            ),
        }

    if "%" in text:
        return {
            "actual": _decimal(text),
            "target": None,
            "unit": "%",
            "compact": False,
        }

    return {
        "actual": _decimal(text),
        "target": None,
        "unit": "",
        "compact": bool(
            re.search(
                r"[KMB]",
                text,
                flags=re.IGNORECASE,
            )
        ),
    }


def _display_part_kpi(kpi):
    actual = kpi.actual_value
    target = kpi.target_value

    if target is not None:
        return (
            f"{_format_number(actual, compact=kpi.compact_numbers)}"
            f" / "
            f"{_format_number(target, compact=kpi.compact_numbers)}"
        )

    if kpi.unit == "%":
        return _format_percentage(
            actual
        )

    return _format_number(
        actual,
        compact=kpi.compact_numbers,
    )


def _display_snapshot_value(kpi):
    actual = _format_number(
        kpi.actual_value,
        compact=kpi.compact_numbers,
    )

    if kpi.target_value is None:
        return actual

    target = _format_number(
        kpi.target_value,
        compact=kpi.compact_numbers,
    )

    return (
        f"{actual} / {target}"
    )


# ==========================================================
# CALCULATIONS
# ==========================================================

def _calculate_dates(dashboard):
    start = dashboard.start_date
    end = dashboard.end_date

    as_of = (
        dashboard.as_of_date
        or timezone.localdate()
    )

    if not start or not end or end < start:
        return {
            "start": start,
            "end": end,
            "as_of": as_of,
            "total_days": 0,
            "elapsed": 0,
            "remaining": 0,
            "total_weeks": 0,
            "current_week": 1,
            "week_start": None,
            "week_end": None,
        }

    total_days = (
        (end - start).days + 1
    )

    elapsed = (
        (as_of - start).days + 1
    )

    elapsed = max(
        0,
        min(
            total_days,
            elapsed,
        ),
    )

    remaining = max(
        0,
        total_days - elapsed,
    )

    total_weeks = math.ceil(
        total_days / 7
    )

    current_week = max(
        1,
        min(
            total_weeks,
            math.ceil(
                elapsed / 7
            ) or 1,
        ),
    )

    week_start = (
        start
        + timedelta(
            days=(
                current_week - 1
            ) * 7
        )
    )

    week_end = min(
        end,
        week_start
        + timedelta(
            days=6
        ),
    )

    return {
        "start": start,
        "end": end,
        "as_of": as_of,
        "total_days": total_days,
        "elapsed": elapsed,
        "remaining": remaining,
        "total_weeks": total_weeks,
        "current_week": current_week,
        "week_start": week_start,
        "week_end": week_end,
    }


def _calculate_part_progress(
    dashboard,
    part,
):
    if (
        not dashboard.calculation_enabled
        or dashboard.parts_mode
        == ProjectDashboard.PartsMode.MANUAL
    ):
        return _round_percentage(
            part.progress
        )

    percentages = []

    for kpi in part.kpis.filter(
        is_active=True
    ):
        if not kpi.include_in_progress:
            continue

        if (
            kpi.target_value is not None
            and kpi.target_value > 0
            and kpi.actual_value is not None
        ):
            percentage = (
                kpi.actual_value
                / kpi.target_value
                * Decimal("100")
            )

            percentages.append(
                _clamp_percentage(
                    percentage
                )
            )

            continue

        if (
            kpi.unit == "%"
            and kpi.actual_value is not None
        ):
            percentages.append(
                _clamp_percentage(
                    kpi.actual_value
                )
            )

    if not percentages:
        return _round_percentage(
            part.progress
        )

    average = (
        sum(
            percentages,
            Decimal("0"),
        )
        / Decimal(
            len(percentages)
        )
    )

    return _round_percentage(
        average
    )


def _weekly_rows(
    dashboard,
    dates,
):
    rows = []

    weekly_records = dashboard.weekly_progress.filter(
        is_active=True
    ).order_by(
        "week_number"
    )

    for record in weekly_records:
        planned = (
            record.planned_progress
        )

        if (
            dashboard.calculation_enabled
            and dashboard.plan_mode
            == ProjectDashboard.PlanMode.LINEAR
            and dates["total_weeks"]
        ):
            planned = (
                Decimal(
                    record.week_number
                )
                / Decimal(
                    dates["total_weeks"]
                )
                * Decimal("100")
            )

        actual = (
            record.actual_progress
        )

        if (
            dashboard.calculation_enabled
            and dashboard.variance_mode
            == ProjectDashboard.AutoManualMode.AUTO
        ):
            variance = None

            if (
                planned is not None
                and actual is not None
            ):
                variance = (
                    actual - planned
                )
        else:
            variance = (
                record.manual_variance
            )

        if (
            dashboard.calculation_enabled
            and dashboard.status_mode
            == ProjectDashboard.AutoManualMode.AUTO
        ):
            status_value = (
                DashboardWeeklyProgress.Status.DONE
                if actual is not None
                else DashboardWeeklyProgress.Status.WAIT
            )
        else:
            status_value = (
                record.status
            )

        if (
            dashboard.calculation_enabled
            and dashboard.periods_mode
            == ProjectDashboard.AutoManualMode.AUTO
            and dashboard.start_date
        ):
            period_start = (
                dashboard.start_date
                + timedelta(
                    days=(
                        record.week_number
                        - 1
                    )
                    * 7
                )
            )

            period_end = (
                period_start
                + timedelta(
                    days=6
                )
            )

            if dashboard.end_date:
                period_end = min(
                    period_end,
                    dashboard.end_date,
                )

            period = _format_date_range(
                period_start,
                period_end,
                include_year=False,
            )

        elif record.manual_period_label:
            period = (
                record.manual_period_label
            )

        elif (
            record.period_start
            and record.period_end
        ):
            period = _format_date_range(
                record.period_start,
                record.period_end,
                include_year=False,
            )

        else:
            period = ""

        rows.append(
            {
                "week_number": (
                    record.week_number
                ),
                "week": (
                    f"W{record.week_number}"
                ),
                "period": period,
                "planned": planned,
                "actual": actual,
                "variance_value": variance,
                "status": status_value,
                "payload": {
                    "week": (
                        f"W{record.week_number}"
                    ),
                    "period": period,
                    "plan": _format_percentage(
                        planned
                    ),
                    "actual": (
                        _format_percentage(
                            actual
                        )
                        if actual is not None
                        else "-"
                    ),
                    "variance": (
                        _format_variance(
                            variance
                        )
                        if variance
                        is not None
                        else "-"
                    ),
                    "status": status_value,
                },
            }
        )

    return rows


def _calculate_overall(
    dashboard,
    parts,
    weekly,
):
    if (
        not dashboard.calculation_enabled
        or dashboard.overall_mode
        == ProjectDashboard.OverallMode.MANUAL
    ):
        return _round_percentage(
            dashboard.overall_progress
        )

    if (
        dashboard.overall_mode
        == ProjectDashboard.OverallMode.WEEKLY
    ):
        for row in reversed(
            weekly
        ):
            if row["actual"] is not None:
                return _round_percentage(
                    row["actual"]
                )

        return _round_percentage(
            dashboard.overall_progress
        )

    if (
        dashboard.overall_mode
        == ProjectDashboard.OverallMode.PARTS
    ):
        weighted_total = Decimal(
            "0"
        )
        total_weight = Decimal(
            "0"
        )

        for part_data in parts:
            weight = Decimal(
                str(
                    part_data["weight"]
                    or 1
                )
            )

            weighted_total += (
                Decimal(
                    str(
                        part_data[
                            "progress"
                        ]
                    )
                )
                * weight
            )

            total_weight += weight

        if total_weight > 0:
            return _round_percentage(
                weighted_total
                / total_weight
            )

    return _round_percentage(
        dashboard.overall_progress
    )


def _calculate_health(
    dashboard,
    weekly,
):
    if (
        not dashboard.calculation_enabled
        or dashboard.health_mode
        == ProjectDashboard.AutoManualMode.MANUAL
    ):
        status = (
            dashboard.manual_health_status
        )

        return {
            "value": (
                "AT RISK"
                if status
                == ProjectDashboard.HealthStatus.AT_RISK
                else status
            ),
            "sub": (
                dashboard.manual_health_subtitle
            ),
        }

    last_variance = None

    for row in reversed(
        weekly
    ):
        if (
            row["actual"] is not None
            and row["planned"]
            is not None
        ):
            last_variance = (
                row["actual"]
                - row["planned"]
            )
            break

    if (
        last_variance is None
        or last_variance >= 0
    ):
        return {
            "value": "GOOD",
            "sub": "On Track",
        }

    if last_variance >= -5:
        return {
            "value": "WATCH",
            "sub": "Minor Slippage",
        }

    return {
        "value": "AT RISK",
        "sub": "Action Required",
    }


def _calculate_nodes(
    dashboard,
    dates,
    phases,
):
    if (
        not dashboard.calculation_enabled
        or dashboard.nodes_mode
        == ProjectDashboard.AutoManualMode.MANUAL
    ):
        return list(
            dashboard.manual_nodes
            or []
        )

    total_nodes = sum(
        max(
            1,
            int(
                phase["span"]
            ),
        )
        for phase in phases
    )

    if total_nodes <= 0:
        total_nodes = (
            dates["total_weeks"]
        )

    current_week = (
        dates["current_week"]
    )

    planned_window = (
        dashboard.planned_window
    )

    nodes = []

    for number in range(
        1,
        total_nodes + 1,
    ):
        if number < current_week:
            nodes.append(
                "completed"
            )
        elif number == current_week:
            nodes.append(
                "progress"
            )
        elif (
            number
            <= current_week
            + planned_window
        ):
            nodes.append(
                "planned"
            )
        else:
            nodes.append(
                "pending"
            )

    return nodes


def _snapshot_percentage(
    dashboard,
    kpi,
):
    if (
        not dashboard.calculation_enabled
        or dashboard.snapshot_mode
        == ProjectDashboard.AutoManualMode.MANUAL
    ):
        return (
            kpi.manual_percentage
        )

    if (
        kpi.target_value is None
        or kpi.target_value <= 0
    ):
        return (
            kpi.manual_percentage
        )

    return _clamp_percentage(
        (
            kpi.actual_value
            / kpi.target_value
        )
        * Decimal("100")
    )


# ==========================================================
# BUILD EXACT FRONTEND-SHAPED RESPONSE
# ==========================================================

def build_dashboard_payload(
    dashboard,
):
    dates = _calculate_dates(
        dashboard
    )

    brand = {
        **DEFAULT_BRAND,
        **(
            dashboard.brand_config
            or {}
        ),
    }

    titles = {
        **DEFAULT_SECTION_TITLES,
        **(
            dashboard.section_titles
            or {}
        ),
    }

    part_payload = []
    calculated_parts = []

    parts = dashboard.parts.filter(
        is_active=True
    ).order_by(
        "display_order",
        "number",
    )

    for part in parts:
        progress = (
            _calculate_part_progress(
                dashboard,
                part,
            )
        )

        kpis = []

        for kpi in part.kpis.filter(
            is_active=True
        ).order_by(
            "display_order",
            "id",
        ):
            kpis.append(
                {
                    "l": kpi.label,
                    "v": (
                        _display_part_kpi(
                            kpi
                        )
                    ),
                }
            )

        item = {
            "num": part.number,
            "name": part.name,
            "icon": part.icon,
            "progress": progress,
            "status": (
                part.get_status_display()
            ),
            "color": part.color,
            "weight": (
                _clean_decimal(
                    part.weight
                )
            ),
            "kpis": kpis,
        }

        part_payload.append(
            item
        )

        calculated_parts.append(
            item
        )

    weekly = _weekly_rows(
        dashboard,
        dates,
    )

    overall = _calculate_overall(
        dashboard,
        calculated_parts,
        weekly,
    )

    health = _calculate_health(
        dashboard,
        weekly,
    )

    phase_payload = []

    phases = dashboard.phases.filter(
        is_active=True
    ).order_by(
        "display_order",
        "id",
    )

    for phase in phases:
        span = max(
            1,
            phase.span_weeks,
        )

        phase_payload.append(
            {
                "name": phase.name,
                "weeks": (
                    f"({span} "
                    f"{'WEEK' if span == 1 else 'WEEKS'})"
                ),
                "span": span,
            }
        )

    nodes = _calculate_nodes(
        dashboard,
        dates,
        phase_payload,
    )

    if (
        dashboard.calculation_enabled
        and dashboard.titles_mode
        == ProjectDashboard.AutoManualMode.AUTO
    ):
        timeline_title = (
            f"EXECUTION TIMELINE "
            f"({len(nodes)} WEEKS)"
        )

        upcoming_week = min(
            dates["current_week"] + 1,
            len(nodes)
            or dates["total_weeks"]
            or 1,
        )

        upcoming_title = (
            f"UPCOMING NEXT WEEK "
            f"(WEEK {upcoming_week})"
        )
    else:
        timeline_title = (
            titles["timelineTitle"]
        )
        upcoming_title = (
            titles["upcomingTitle"]
        )

    overrides = (
        dashboard.stat_overrides
        or {}
    )

    duration_override = (
        overrides.get(
            "duration",
            {},
        )
    )

    week_override = (
        overrides.get(
            "currentWeek",
            {},
        )
    )

    elapsed_override = (
        overrides.get(
            "daysElapsed",
            {},
        )
    )

    remaining_override = (
        overrides.get(
            "daysRemaining",
            {},
        )
    )

    if (
        dashboard.calculation_enabled
        and dashboard.duration_mode
        == ProjectDashboard.AutoManualMode.AUTO
        and dates["total_weeks"]
    ):
        duration_value = (
            f"{dates['total_weeks']} WEEKS"
        )

        duration_sub = (
            f"("
            f"{_format_short_date(dates['start'])}"
            f" – "
            f"{_format_date(dates['end'])}"
            f")"
        )
    else:
        duration_value = (
            duration_override.get(
                "value",
                "",
            )
        )
        duration_sub = (
            duration_override.get(
                "sub",
                "",
            )
        )

    if (
        dashboard.calculation_enabled
        and dashboard.current_week_mode
        == ProjectDashboard.AutoManualMode.AUTO
        and dates["week_start"]
    ):
        current_week_value = (
            f"WEEK "
            f"{dates['current_week']}"
        )

        current_week_sub = (
            f"("
            f"{_format_date_range(
                dates['week_start'],
                dates['week_end'],
                include_year=True,
            )}"
            f")"
        )
    else:
        current_week_value = (
            week_override.get(
                "value",
                "",
            )
        )

        current_week_sub = (
            week_override.get(
                "sub",
                "",
            )
        )

    if (
        dashboard.calculation_enabled
        and dashboard.days_mode
        == ProjectDashboard.AutoManualMode.AUTO
        and dates["total_days"]
    ):
        elapsed_value = (
            f"{dates['elapsed']} / "
            f"{dates['total_days']}"
        )

        elapsed_sub = "Days"

        remaining_value = str(
            dates["remaining"]
        )

        remaining_sub = "Days"
    else:
        elapsed_value = (
            elapsed_override.get(
                "value",
                "",
            )
        )
        elapsed_sub = (
            elapsed_override.get(
                "sub",
                "Days",
            )
        )

        remaining_value = (
            remaining_override.get(
                "value",
                "",
            )
        )
        remaining_sub = (
            remaining_override.get(
                "sub",
                "Days",
            )
        )

    stats = [
        {
            "icon": "calendar",
            "label": "PROJECT DURATION",
            "value": duration_value,
            "sub": duration_sub,
            "bind": "duration",
        },
        {
            "icon": "calendar",
            "label": "CURRENT WEEK",
            "value": current_week_value,
            "sub": current_week_sub,
            "bind": "currentWeek",
        },
        {
            "icon": "pulse",
            "label": "PROJECT HEALTH",
            "value": health["value"],
            "sub": health["sub"],
            "health": True,
            "bind": "health",
        },
        {
            "icon": "target",
            "label": "OVERALL PROGRESS",
            "value": f"{overall}%",
            "sub": (
                dashboard.overall_caption
            ),
            "bind": "overall",
        },
        {
            "icon": "calendar",
            "label": "DAYS ELAPSED",
            "value": elapsed_value,
            "sub": elapsed_sub,
            "bind": "daysElapsed",
        },
        {
            "icon": "hourglass",
            "label": "DAYS REMAINING",
            "value": remaining_value,
            "sub": remaining_sub,
            "bind": "daysRemaining",
        },
    ]

    highlights = list(
        dashboard.update_items.filter(
            is_active=True,
            item_type=(
                DashboardUpdateItem.ItemType.HIGHLIGHT
            ),
        )
        .order_by(
            "display_order",
            "id",
        )
        .values_list(
            "text",
            flat=True,
        )
    )

    upcoming = list(
        dashboard.update_items.filter(
            is_active=True,
            item_type=(
                DashboardUpdateItem.ItemType.UPCOMING
            ),
        )
        .order_by(
            "display_order",
            "id",
        )
        .values_list(
            "text",
            flat=True,
        )
    )

    risks = []

    for risk in dashboard.risk_summaries.filter(
        is_active=True
    ).order_by(
        "display_order",
        "id",
    ):
        risks.append(
            {
                "icon": risk.icon,
                "label": risk.label,
                "value": str(
                    risk.value
                ),
                "sub": risk.sub_text,
                "color": risk.color,
            }
        )

    snapshot = []

    for kpi in dashboard.snapshot_kpis.filter(
        is_active=True
    ).order_by(
        "display_order",
        "id",
    ):
        percentage = (
            _snapshot_percentage(
                dashboard,
                kpi,
            )
        )

        snapshot.append(
            {
                "icon": kpi.icon,
                "label": kpi.label,
                "value": (
                    _display_snapshot_value(
                        kpi
                    )
                ),
                "pct": (
                    _format_percentage(
                        percentage
                    )
                    if percentage
                    is not None
                    else "-"
                ),
                "color": kpi.color,
            }
        )

    stakeholder_rows = []

    for item in (
        dashboard.stakeholder_actions.filter(
            is_active=True
        )
        .order_by(
            "display_order",
            "due_date",
            "id",
        )
    ):
        stakeholder_rows.append(
            {
                "who": item.stakeholder,
                "action": item.action,
                "due": (
                    _format_date(
                        item.due_date
                    )
                    if item.due_date
                    else ""
                ),
                "status": item.status,
            }
        )

    return {
        "brand": brand,
        "header": {
            "eyebrow": (
                dashboard.eyebrow
            ),
            "title": (
                dashboard.dashboard_title
            ),
            "subtitle": (
                dashboard.dashboard_subtitle
            ),
            "updatedLabel": (
                "LAST UPDATED"
            ),
            "updatedDate": (
                _display_updated_date(
                    dashboard.updated_at
                )
            ),
            "updatedTime": (
                _display_time(
                    dashboard.updated_at
                )
            ),
            "pmLabel": (
                "REPORTING PM"
            ),
            "pmName": (
                dashboard.reporting_pm_name
            ),
            "pmRole": (
                dashboard.reporting_pm_role
            ),
        },
        "stats": stats,
        "partsTitle": (
            titles["partsTitle"]
        ),
        "parts": part_payload,
        "overallTitle": (
            titles["overallTitle"]
        ),
        "overall": {
            "percent": overall,
            "caption": (
                dashboard.overall_caption
            ),
            "minLabel": "0%",
            "maxLabel": "100%",
        },
        "timelineTitle": (
            timeline_title
        ),
        "phases": phase_payload,
        "nodes": nodes,
        "legend": (
            dashboard.legend_config
            or DEFAULT_LEGEND
        ),
        "highlightsTitle": (
            titles["highlightsTitle"]
        ),
        "highlights": highlights,
        "upcomingTitle": (
            upcoming_title
        ),
        "upcoming": upcoming,
        "weeklyTitle": (
            titles["weeklyTitle"]
        ),
        "weekly": [
            item["payload"]
            for item in weekly
        ],
        "riskTitle": (
            titles["riskTitle"]
        ),
        "risks": risks,
        "snapTitle": (
            titles["snapTitle"]
        ),
        "snapshot": snapshot,
        "stakeTitle": (
            titles["stakeTitle"]
        ),
        "stakeHead": (
            dashboard.stakeholder_headers
            or DEFAULT_STAKEHOLDER_HEADERS
        ),
        "stakeholders": (
            stakeholder_rows
        ),
        "footer": (
            dashboard.footer_config
            or []
        ),
        "auto": {
            "enabled": (
                dashboard.calculation_enabled
            ),
            "startDate": (
                dashboard.start_date.isoformat()
                if dashboard.start_date
                else ""
            ),
            "endDate": (
                dashboard.end_date.isoformat()
                if dashboard.end_date
                else ""
            ),
            "asOfDate": (
                dashboard.as_of_date.isoformat()
                if dashboard.as_of_date
                else ""
            ),
            "overallMode": (
                dashboard.overall_mode
            ),
            "partsMode": (
                dashboard.parts_mode
            ),
            "varianceMode": (
                dashboard.variance_mode
            ),
            "statusMode": (
                dashboard.status_mode
            ),
            "planMode": (
                dashboard.plan_mode
            ),
            "periodsMode": (
                dashboard.periods_mode
            ),
            "nodesMode": (
                dashboard.nodes_mode
            ),
            "plannedWindow": (
                dashboard.planned_window
            ),
            "snapshotMode": (
                dashboard.snapshot_mode
            ),
            "healthMode": (
                dashboard.health_mode
            ),
            "daysMode": (
                dashboard.days_mode
            ),
            "durationMode": (
                dashboard.duration_mode
            ),
            "currentWeekMode": (
                dashboard.current_week_mode
            ),
            "titlesMode": (
                dashboard.titles_mode
            ),
        },
    }


# ==========================================================
# UPDATE FROM EXISTING FRONTEND JSON STRUCTURE
# ==========================================================

def _extract_stat_overrides(
    payload,
):
    result = {}

    for item in payload.get(
        "stats",
        [],
    ):
        bind = item.get(
            "bind"
        )

        if not bind:
            continue

        result[bind] = {
            "value": item.get(
                "value",
                "",
            ),
            "sub": item.get(
                "sub",
                "",
            ),
        }

    return result


@transaction.atomic
def update_dashboard_from_payload(
    dashboard,
    payload,
    *,
    user=None,
):
    brand = payload.get(
        "brand",
        {},
    )

    header = payload.get(
        "header",
        {},
    )

    auto = payload.get(
        "auto",
        {},
    )

    overall = payload.get(
        "overall",
        {},
    )

    dashboard.brand_config = brand

    dashboard.eyebrow = (
        header.get(
            "eyebrow",
            dashboard.eyebrow,
        )
    )

    dashboard.dashboard_title = (
        header.get(
            "title",
            dashboard.dashboard_title,
        )
    )

    dashboard.dashboard_subtitle = (
        header.get(
            "subtitle",
            dashboard.dashboard_subtitle,
        )
    )

    dashboard.reporting_pm_name = (
        header.get(
            "pmName",
            dashboard.reporting_pm_name,
        )
    )

    dashboard.reporting_pm_role = (
        header.get(
            "pmRole",
            dashboard.reporting_pm_role,
        )
    )

    dashboard.overall_progress = (
        _decimal(
            overall.get(
                "percent"
            ),
            dashboard.overall_progress,
        )
    )

    dashboard.overall_caption = (
        overall.get(
            "caption",
            dashboard.overall_caption,
        )
    )

    dashboard.calculation_enabled = (
        bool(
            auto.get(
                "enabled",
                dashboard.calculation_enabled,
            )
        )
    )

    dashboard.start_date = (
        _date_from_value(
            auto.get(
                "startDate"
            )
        )
        or dashboard.start_date
    )

    dashboard.end_date = (
        _date_from_value(
            auto.get(
                "endDate"
            )
        )
        or dashboard.end_date
    )

    as_of_raw = auto.get(
        "asOfDate"
    )

    if as_of_raw in {
        "",
        None,
    }:
        dashboard.as_of_date = None
    else:
        dashboard.as_of_date = (
            _date_from_value(
                as_of_raw
            )
        )

    mode_fields = {
        "overallMode": "overall_mode",
        "partsMode": "parts_mode",
        "varianceMode": "variance_mode",
        "statusMode": "status_mode",
        "planMode": "plan_mode",
        "periodsMode": "periods_mode",
        "nodesMode": "nodes_mode",
        "snapshotMode": "snapshot_mode",
        "healthMode": "health_mode",
        "daysMode": "days_mode",
        "durationMode": "duration_mode",
        "currentWeekMode": (
            "current_week_mode"
        ),
        "titlesMode": "titles_mode",
    }

    for source, target in (
        mode_fields.items()
    ):
        if source in auto:
            setattr(
                dashboard,
                target,
                auto[source],
            )

    if "plannedWindow" in auto:
        dashboard.planned_window = (
            max(
                0,
                _integer(
                    auto["plannedWindow"],
                    default=5,
                ),
            )
        )

    dashboard.manual_nodes = (
        payload.get(
            "nodes",
            [],
        )
    )

    dashboard.legend_config = (
        payload.get(
            "legend",
            [],
        )
    )

    dashboard.footer_config = (
        payload.get(
            "footer",
            [],
        )
    )

    dashboard.stakeholder_headers = (
        payload.get(
            "stakeHead",
            DEFAULT_STAKEHOLDER_HEADERS,
        )
    )

    dashboard.stat_overrides = (
        _extract_stat_overrides(
            payload
        )
    )

    title_keys = (
        "partsTitle",
        "overallTitle",
        "timelineTitle",
        "highlightsTitle",
        "upcomingTitle",
        "weeklyTitle",
        "riskTitle",
        "snapTitle",
        "stakeTitle",
    )

    section_titles = {
        key: payload[key]
        for key in title_keys
        if key in payload
    }

    dashboard.section_titles = (
        section_titles
    )

    health_stat = next(
        (
            item
            for item
            in payload.get(
                "stats",
                [],
            )
            if item.get(
                "bind"
            )
            == "health"
        ),
        None,
    )

    if health_stat:
        health_value = (
            str(
                health_stat.get(
                    "value",
                    "",
                )
            )
            .strip()
            .upper()
            .replace(
                " ",
                "_",
            )
        )

        if health_value in {
            choice
            for choice, _
            in ProjectDashboard.HealthStatus.choices
        }:
            dashboard.manual_health_status = (
                health_value
            )

        dashboard.manual_health_subtitle = (
            health_stat.get(
                "sub",
                dashboard.manual_health_subtitle,
            )
        )

    if user:
        if not dashboard.created_by_id:
            dashboard.created_by = user

        dashboard.updated_by = user

    dashboard.save()

    # ------------------------------------------------------
    # Child data is replaced transactionally.
    #
    # The frontend edits one complete dashboard document, and
    # child IDs are not exposed/used by the UI.
    # ------------------------------------------------------

    dashboard.phases.all().delete()
    dashboard.parts.all().delete()
    dashboard.weekly_progress.all().delete()
    dashboard.update_items.all().delete()
    dashboard.risk_summaries.all().delete()
    dashboard.snapshot_kpis.all().delete()
    dashboard.stakeholder_actions.all().delete()

    audit = _audit_kwargs(
        user
    )

    # ------------------------------------------------------
    # PHASES
    # ------------------------------------------------------

    for order, item in enumerate(
        payload.get(
            "phases",
            [],
        )
    ):
        DashboardPhase.objects.create(
            dashboard=dashboard,
            name=item.get(
                "name",
                f"Phase {order + 1}",
            ),
            span_weeks=max(
                1,
                _integer(
                    item.get(
                        "span",
                        1,
                    ),
                    default=1,
                ),
            ),
            display_order=order,
            **audit,
        )

    # ------------------------------------------------------
    # PARTS + PART KPIs
    # ------------------------------------------------------

    for order, item in enumerate(
        payload.get(
            "parts",
            [],
        )
    ):
        raw_status = (
            str(
                item.get(
                    "status",
                    "On Track",
                )
            )
            .strip()
            .lower()
        )

        status_value = (
            PART_STATUS_MAP.get(
                raw_status,
                DashboardPart.Status.ON_TRACK,
            )
        )

        part = DashboardPart.objects.create(
            dashboard=dashboard,
            number=_integer(
                item.get(
                    "num",
                    order + 1,
                ),
                default=order + 1,
            ),
            name=item.get(
                "name",
                f"Part {order + 1}",
            ),
            icon=item.get(
                "icon",
                "",
            ),
            progress=_decimal(
                item.get(
                    "progress",
                    0,
                ),
                Decimal("0"),
            ),
            status=status_value,
            color=item.get(
                "color",
                "#2E9E33",
            ),
            weight=_decimal(
                item.get(
                    "weight",
                    1,
                ),
                Decimal("1"),
            ),
            display_order=order,
            **audit,
        )

        for kpi_order, kpi_data in enumerate(
            item.get(
                "kpis",
                [],
            )
        ):
            parsed = (
                _parse_kpi_display_value(
                    kpi_data.get(
                        "v",
                        "",
                    )
                )
            )

            DashboardPartKPI.objects.create(
                part=part,
                label=kpi_data.get(
                    "l",
                    f"KPI {kpi_order + 1}",
                ),
                actual_value=(
                    parsed["actual"]
                ),
                target_value=(
                    parsed["target"]
                ),
                unit=parsed["unit"],
                compact_numbers=(
                    parsed["compact"]
                ),
                include_in_progress=(
                    parsed["target"]
                    is not None
                    or parsed["unit"]
                    == "%"
                ),
                display_order=(
                    kpi_order
                ),
                **audit,
            )

    # ------------------------------------------------------
    # WEEKLY
    # ------------------------------------------------------

    for order, item in enumerate(
        payload.get(
            "weekly",
            [],
        )
    ):
        week_number = (
            _integer(
                re.sub(
                    r"\D",
                    "",
                    str(
                        item.get(
                            "week",
                            order + 1,
                        )
                    ),
                ),
                default=order + 1,
            )
        )

        DashboardWeeklyProgress.objects.create(
            dashboard=dashboard,
            week_number=week_number,
            manual_period_label=item.get(
                "period",
                "",
            ),
            planned_progress=_decimal(
                item.get(
                    "plan"
                )
            ),
            actual_progress=_decimal(
                item.get(
                    "actual"
                )
            ),
            manual_variance=_decimal(
                item.get(
                    "variance"
                )
            ),
            status=item.get(
                "status",
                DashboardWeeklyProgress.Status.WAIT,
            ),
            **audit,
        )

    # ------------------------------------------------------
    # HIGHLIGHTS
    # ------------------------------------------------------

    for order, text in enumerate(
        payload.get(
            "highlights",
            [],
        )
    ):
        DashboardUpdateItem.objects.create(
            dashboard=dashboard,
            item_type=(
                DashboardUpdateItem.ItemType.HIGHLIGHT
            ),
            text=str(text),
            display_order=order,
            **audit,
        )

    # ------------------------------------------------------
    # UPCOMING
    # ------------------------------------------------------

    for order, text in enumerate(
        payload.get(
            "upcoming",
            [],
        )
    ):
        DashboardUpdateItem.objects.create(
            dashboard=dashboard,
            item_type=(
                DashboardUpdateItem.ItemType.UPCOMING
            ),
            text=str(text),
            display_order=order,
            **audit,
        )

    # ------------------------------------------------------
    # RISKS
    # ------------------------------------------------------

    for order, item in enumerate(
        payload.get(
            "risks",
            [],
        )
    ):
        label = item.get(
            "label",
            f"Risk {order + 1}",
        )

        key = (
            item.get("key")
            or slugify(label)
            or f"risk-{order + 1}"
        )

        DashboardRiskSummary.objects.create(
            dashboard=dashboard,
            key=key[:50],
            icon=item.get(
                "icon",
                "",
            ),
            label=label,
            value=max(
                0,
                _integer(
                    item.get(
                        "value",
                        0,
                    ),
                    default=0,
                ),
            ),
            sub_text=item.get(
                "sub",
                "",
            ),
            color=item.get(
                "color",
                "#2E9E33",
            ),
            display_order=order,
            **audit,
        )

    # ------------------------------------------------------
    # SNAPSHOT KPIs
    # ------------------------------------------------------

    for order, item in enumerate(
        payload.get(
            "snapshot",
            [],
        )
    ):
        label = item.get(
            "label",
            f"KPI {order + 1}",
        )

        parsed = (
            _parse_kpi_display_value(
                item.get(
                    "value",
                    "",
                )
            )
        )

        key = (
            item.get("key")
            or slugify(label)
            or f"kpi-{order + 1}"
        )

        DashboardSnapshotKPI.objects.create(
            dashboard=dashboard,
            key=key[:60],
            icon=item.get(
                "icon",
                "",
            ),
            label=label,
            actual_value=(
                parsed["actual"]
                or Decimal("0")
            ),
            target_value=(
                parsed["target"]
            ),
            unit=(
                "PKR"
                if "PKR"
                in label.upper()
                else parsed["unit"]
            ),
            compact_numbers=(
                parsed["compact"]
            ),
            manual_percentage=_decimal(
                item.get(
                    "pct"
                )
            ),
            color=item.get(
                "color",
                "#2E9E33",
            ),
            display_order=order,
            **audit,
        )

    # ------------------------------------------------------
    # STAKEHOLDERS
    # ------------------------------------------------------

    for order, item in enumerate(
        payload.get(
            "stakeholders",
            [],
        )
    ):
        DashboardStakeholderAction.objects.create(
            dashboard=dashboard,
            stakeholder=item.get(
                "who",
                "",
            ),
            action=item.get(
                "action",
                "",
            ),
            due_date=_date_from_value(
                item.get(
                    "due"
                )
            ),
            status=item.get(
                "status",
                DashboardStakeholderAction.Status.WAIT,
            ),
            display_order=order,
            **audit,
        )

    return dashboard
