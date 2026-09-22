from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from User.models import Role


class Command(BaseCommand):
    help = (
        "Create/update the fixed LIMS dashboard users."
    )

    DASHBOARD_USERS = [
        {
            "username": "admin",
            "password": "Admin@123",
            "role": "Admin",
            "mobile_number": "0000000001",
        },
        {
            "username": "ceo",
            "password": "Ceo@123",
            "role": "CEO",
            "mobile_number": "0000000002",
        },
        {
            "username": "guest",
            "password": "Guest@123",
            "role": "Guest",
            "mobile_number": "0000000003",
        },
    ]

    def handle(self, *args, **options):
        User = get_user_model()

        for item in self.DASHBOARD_USERS:
            role, _ = Role.objects.get_or_create(
                name=item["role"]
            )

            user, created = User.objects.get_or_create(
                username=item["username"],
                defaults={
                    "mobile_number": (
                        item["mobile_number"]
                    ),
                    "role": role,
                },
            )

            user.role = role
            user.is_active = True

            user.set_password(
                item["password"]
            )

            user.save()

            action = (
                "Created"
                if created
                else "Updated"
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"{action}: "
                    f"{item['username']} "
                    f"({item['role']})"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Dashboard users seeded successfully."
            )
        )
