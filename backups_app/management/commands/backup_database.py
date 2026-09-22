"""
management/commands/backup_database.py
---------------------------------------
Creates a pg_dump backup of the production database.

Runs daily via crontab but only writes a file when
backup_interval_days have elapsed since the last backup.

Crontab entry (run as the app user):
    0 0 * * * /path/to/venv/bin/python /path/to/manage.py backup_database

Backups are saved to:
    <project_root>/backups/db_backup_YYYYMMDD_HHMMSS.dump

Old backups are rotated: only the most recent backup_keep_count files are kept.
"""

import os
import subprocess
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Create a pg_dump database backup if the interval has elapsed."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force a backup regardless of the interval.",
        )

    def handle(self, *args, **options):
        from backups_app.models import CronConfig
        config = CronConfig.get()

        force = options.get("force", False)

        # Check interval
        if not force and config.last_backup_at:
            elapsed = timezone.now() - config.last_backup_at
            if elapsed < timedelta(days=config.backup_interval_days):
                next_due = config.last_backup_at + timedelta(
                    days=config.backup_interval_days
                )
                self.stdout.write(
                    f"Skipping backup — next due at {next_due.strftime('%Y-%m-%d %H:%M')} "
                    f"(interval: {config.backup_interval_days} days)."
                )
                return

        # Prepare backup directory
        backup_dir = Path(settings.BASE_DIR) / "backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        filename = backup_dir / f"db_backup_{timestamp}.dump"

        # Read DB settings
        db = settings.DATABASES["default"]
        db_name = db.get("NAME", "")
        db_user = db.get("USER", "")
        db_password = db.get("PASSWORD", "")
        db_host = db.get("HOST", "localhost")
        db_port = db.get("PORT", "5432")

        env = os.environ.copy()
        env["PGPASSWORD"] = db_password

        cmd = [
            "pg_dump",
            "-Fc",
            "-h", db_host,
            "-p", str(db_port),
            "-U", db_user,
            db_name,
            "-f", str(filename),
        ]

        self.stdout.write(f"Starting backup → {filename}")

        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode != 0:
                self.stderr.write(f"pg_dump failed:\n{result.stderr}")
                return

            size_mb = filename.stat().st_size / (1024 * 1024)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Backup complete: {filename.name} ({size_mb:.1f} MB)"
                )
            )

            # Update last_backup_at
            config.last_backup_at = timezone.now()
            config.save(update_fields=["last_backup_at"])

        except subprocess.TimeoutExpired:
            self.stderr.write("pg_dump timed out after 5 minutes.")
            return
        except FileNotFoundError:
            self.stderr.write(
                "pg_dump not found. Install postgresql-client on the server."
            )
            return

        # Rotate old backups — keep only the most recent N files
        all_backups = sorted(backup_dir.glob("db_backup_*.dump"))
        to_delete = all_backups[: -config.backup_keep_count]
        for old in to_delete:
            old.unlink()
            self.stdout.write(f"Rotated old backup: {old.name}")

        self.stdout.write(
            f"Backups retained: {min(len(all_backups), config.backup_keep_count)}"
        )
