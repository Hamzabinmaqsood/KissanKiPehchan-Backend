import requests
from datetime import date
from .models import MandiDailyData


def fetch_and_save_mandi(for_date=None, department="LIMS"):
    """
    Fetch mandi rates from the AMIS API for the given date and department,
    then cache the full response in MandiDailyData.

    Args:
        for_date:   date object. Defaults to today.
        department: AMIS department code. Defaults to "LIMS".
                    Configurable via CronConfig.mandi_department in Django admin.

    Returns:
        dict with date, total_records, created (bool).
    """
    if for_date is None:
        for_date = date.today()

    url = (
        f"http://amis.pk/Androidforpitb/Prices.ashx"
        f"?date={for_date}&Depart={department}"
    )

    r = requests.get(url, timeout=None)
    r.raise_for_status()

    api_data = r.json()

    obj, created = MandiDailyData.objects.update_or_create(
        date=for_date,
        defaults={"data": api_data},
    )

    # Total records — handle both list and dict response shapes
    if isinstance(api_data, list):
        total = len(api_data)
    elif isinstance(api_data, dict):
        total = api_data.get("total_records", len(api_data.get("data", [])))
    else:
        total = 0

    return {
        "date": str(for_date),
        "total_records": total,
        "created": created,
    }
