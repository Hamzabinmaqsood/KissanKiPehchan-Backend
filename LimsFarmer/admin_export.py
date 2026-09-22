"""
LimsFarmer/admin_export.py
---------------------------
Full-database export to a single Excel file.

Every registered Django admin model is written to its own sheet.
Accessible from the admin homepage via the "Export Full Database" button.

Usage — add to LimsFarmer/urls.py:

    from .admin_export import export_full_database

    urlpatterns += [
        path(
            "api/admin/export-db/",
            export_full_database,
            name="admin-export-db",
        ),
    ]

And add to LimsFarmer/admin_site.py (or templates/admin/index.html override):
The simplest way is to add a direct link to the admin homepage template.
"""

import io
from datetime import datetime

import openpyxl
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse


def _get_field_names(model):
    """
    Return a list of (field_name, verbose_name) for all concrete fields
    on a model, excluding binary/file fields that can't be serialised.
    """
    skip_types = {
        "FileField", "ImageField", "BinaryField",
        "FilePathField",
    }
    fields = []
    for f in model._meta.get_fields():
        # skip reverse relations and M2M
        if f.is_relation and (f.one_to_many or f.many_to_many):
            continue
        if not hasattr(f, "column"):
            continue
        if type(f).__name__ in skip_types:
            continue
        verbose = getattr(f, "verbose_name", f.name)
        fields.append((f.name, str(verbose).title()))
    return fields


def _get_value(obj, field_name):
    """
    Safely retrieve a field value from a model instance.
    FK fields return their string representation.
    DateTimeField values are made timezone-naive for Excel.
    """
    try:
        value = getattr(obj, field_name)
    except Exception:
        return ""

    if value is None:
        return ""

    # Make datetimes tz-naive so openpyxl can write them
    if hasattr(value, "tzinfo") and value.tzinfo is not None:
        value = value.replace(tzinfo=None)

    # FK / related objects → str
    if hasattr(value, "pk") and not isinstance(value, (str, int, float, bool)):
        return str(value)

    return value


def _write_sheet(wb, model, sheet_name):
    """
    Write all rows of `model` to a new sheet in `wb`.
    Returns the number of rows written.
    """
    ws = wb.create_sheet(title=sheet_name[:31])  # Excel sheet name limit

    fields = _get_field_names(model)
    if not fields:
        ws.append(["(no exportable fields)"])
        return 0

    # Header row
    headers = [verbose for _, verbose in fields]
    ws.append(headers)

    # Style the header
    from openpyxl.styles import Font, PatternFill
    header_fill = PatternFill("solid", fgColor="1F7A33")
    header_font = Font(bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font

    # Data rows
    count = 0
    qs = model.objects.all().order_by("pk") if hasattr(model, "pk") else model.objects.all()

    for obj in qs.iterator(chunk_size=500):
        row = [_get_value(obj, fname) for fname, _ in fields]
        ws.append(row)
        count += 1

    # Auto-width columns (capped at 60)
    for col in ws.columns:
        max_len = max(
            (len(str(cell.value)) for cell in col if cell.value is not None),
            default=10,
        )
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 60)

    return count


@staff_member_required
def export_full_database(request):
    """
    Django view: export all admin-registered models to a single .xlsx file.
    One sheet per model, named after the model's verbose name.
    """
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # remove the default empty sheet

    # Summary sheet first
    summary_ws = wb.create_sheet(title="Export Summary", index=0)
    from openpyxl.styles import Font, PatternFill
    summary_ws.append(["Table", "Rows Exported", "Sheet Name"])
    for cell in summary_ws[1]:
        cell.fill = PatternFill("solid", fgColor="12355B")
        cell.font = Font(bold=True, color="FFFFFF")

    exported = []

    # Walk every registered admin model
    for model, model_admin in admin.site._registry.items():
        app_label = model._meta.app_label
        model_name = model._meta.verbose_name.title()
        sheet_name = f"{app_label[:10]}_{model_name}"[:31]

        # Avoid duplicate sheet names
        existing = [ws.title for ws in wb.worksheets]
        base = sheet_name
        counter = 1
        while sheet_name in existing:
            sheet_name = f"{base[:28]}_{counter}"
            counter += 1

        try:
            count = _write_sheet(wb, model, sheet_name)
            exported.append((model_name, count, sheet_name))
        except Exception as e:
            # Don't let one broken model stop the whole export
            ws = wb.create_sheet(title=sheet_name[:31])
            ws.append([f"Export error: {e}"])
            exported.append((model_name, "ERROR", sheet_name))

    # Fill summary
    for model_name, count, sheet_name in sorted(exported):
        summary_ws.append([model_name, count, sheet_name])

    summary_ws.column_dimensions["A"].width = 35
    summary_ws.column_dimensions["B"].width = 15
    summary_ws.column_dimensions["C"].width = 35

    # Write to response
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"LIMS_FullDB_Export_{timestamp}.xlsx"

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
