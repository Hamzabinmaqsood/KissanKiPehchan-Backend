import json
from pathlib import Path

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from project_dashboard.models import (
    ProjectDashboard,
)
from project_dashboard.serializers import (
    DashboardPayloadSerializer,
)
from project_dashboard.services import (
    update_dashboard_from_payload,
)


class Command(BaseCommand):
    help = (
        "Import the existing AgriOne/K2P dashboard "
        "data.json into PostgreSQL."
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "json_file",
            type=str,
            help="Path to the existing dashboard data.json.",
        )

        parser.add_argument(
            "--project-code",
            default="k2p",
        )

        parser.add_argument(
            "--project-name",
            default="AgriOne-OS (K2P)",
        )

    def handle(
        self,
        *args,
        **options,
    ):
        path = Path(
            options["json_file"]
        ).expanduser().resolve()

        if not path.exists():
            raise CommandError(
                f"File not found: {path}"
            )

        try:
            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as exc:
            raise CommandError(
                f"Invalid JSON: {exc}"
            )

        serializer = (
            DashboardPayloadSerializer(
                data=payload
            )
        )

        if not serializer.is_valid():
            raise CommandError(
                serializer.errors
            )

        dashboard, created = (
            ProjectDashboard.objects.get_or_create(
                project_code=(
                    options[
                        "project_code"
                    ]
                ),
                defaults={
                    "project_name": (
                        options[
                            "project_name"
                        ]
                    ),
                    "project_subtitle": (
                        "Kisan Ki Pehchan"
                    ),
                },
            )
        )

        if not created:
            dashboard.project_name = (
                options[
                    "project_name"
                ]
            )
            dashboard.is_active = True
            dashboard.save(
                update_fields=[
                    "project_name",
                    "is_active",
                    "updated_at",
                ]
            )

        update_dashboard_from_payload(
            dashboard,
            serializer.validated_data,
            user=None,
        )

        action = (
            "Created"
            if created
            else "Updated"
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"{action} dashboard "
                f"'{dashboard.project_code}' successfully."
            )
        )
