"""
management/commands/fetch_mandi_today.py
-----------------------------------------
Fetches today's mandi rates from the AMIS API and caches them in the DB.

Designed to run once daily via crontab at the hour configured in CronConfig.

Crontab entry (run as the app user):
    0 11 * * * /path/to/venv/bin/python /path/to/manage.py fetch_mandi_today

If the fetch fails, the previous day's cached data remains available —
MandiDataView already serves it as a fallback automatically.
"""

from datetime import date

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Fetch today's mandi rates from the AMIS API and cache in the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            default=None,
            help="Date to fetch (YYYY-MM-DD). Defaults to today.",
        )

    def handle(self, *args, **options):
        from mandi.fetcher import fetch_and_save_mandi
        from backups_app.models import CronConfig

        config = CronConfig.get()

        date_str = options.get("date")
        if date_str:
            from django.utils.dateparse import parse_date
            fetch_date = parse_date(date_str)
            if not fetch_date:
                self.stderr.write(f"Invalid date: {date_str}. Use YYYY-MM-DD.")
                return
        else:
            fetch_date = date.today()

        self.stdout.write(
            f"Fetching mandi rates for {fetch_date} "
            f"(dept={config.mandi_department}) ..."
        )

        import time

        MAX_RETRIES = 3
        RETRY_WAIT = 60  # seconds between attempts

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self.stdout.write(f"Attempt {attempt}/{MAX_RETRIES} ...")
                result = fetch_and_save_mandi(
                    for_date=fetch_date,
                    department=config.mandi_department,
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Done — {result['total_records']} records cached "
                        f"for {result['date']} "
                        f"({'created' if result['created'] else 'updated'})."
                    )
                )
                break  # success — stop retrying

            except Exception as e:
                self.stderr.write(f"Attempt {attempt} failed: {e}")
                if attempt < MAX_RETRIES:
                    self.stdout.write(f"Retrying in {RETRY_WAIT}s ...")
                    time.sleep(RETRY_WAIT)
                else:
                    self.stderr.write(
                        f"All {MAX_RETRIES} attempts failed for {fetch_date}.\n"
                        "Previous cached data remains available to users."
                    )
