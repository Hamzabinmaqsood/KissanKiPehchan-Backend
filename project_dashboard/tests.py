from datetime import date
from decimal import Decimal

from django.urls import reverse

from rest_framework import status
from rest_framework.test import (
    APITestCase,
)

from User.models import (
    CustomUser,
    Role,
)

from .models import (
    DashboardPart,
    DashboardPartKPI,
    DashboardWeeklyProgress,
    ProjectDashboard,
)
from .services import (
    build_dashboard_payload,
)


class ProjectDashboardTests(
    APITestCase
):
    def setUp(self):
        self.admin_role = (
            Role.objects.create(
                name="Admin"
            )
        )

        self.farmer_role = (
            Role.objects.create(
                name="Farmer"
            )
        )

        self.admin_user = (
            CustomUser.objects.create_user(
                mobile_number="03000000001",
                password="Test@123",
                role=self.admin_role,
                username="dashboard-admin",
            )
        )

        self.normal_user = (
            CustomUser.objects.create_user(
                mobile_number="03000000002",
                password="Test@123",
                role=self.farmer_role,
                username="farmer-test",
            )
        )

        self.dashboard = (
            ProjectDashboard.objects.create(
                project_code="k2p",
                project_name=(
                    "AgriOne-OS (K2P)"
                ),
                start_date=date(
                    2026,
                    7,
                    15,
                ),
                end_date=date(
                    2026,
                    11,
                    10,
                ),
                as_of_date=date(
                    2026,
                    8,
                    11,
                ),
                overall_mode=(
                    ProjectDashboard
                    .OverallMode
                    .WEEKLY
                ),
            )
        )

        self.part = (
            DashboardPart.objects.create(
                dashboard=self.dashboard,
                number=1,
                name="Software",
                progress=Decimal(
                    "50"
                ),
                display_order=0,
            )
        )

        DashboardPartKPI.objects.create(
            part=self.part,
            label="Modules Completed",
            actual_value=Decimal(
                "5"
            ),
            target_value=Decimal(
                "10"
            ),
            include_in_progress=True,
            display_order=0,
        )

        DashboardPartKPI.objects.create(
            part=self.part,
            label="Unit Test Coverage",
            actual_value=Decimal(
                "80"
            ),
            unit="%",
            include_in_progress=True,
            display_order=1,
        )

        DashboardWeeklyProgress.objects.create(
            dashboard=self.dashboard,
            week_number=1,
            planned_progress=Decimal(
                "10"
            ),
            actual_progress=Decimal(
                "12"
            ),
        )

        DashboardWeeklyProgress.objects.create(
            dashboard=self.dashboard,
            week_number=2,
            planned_progress=Decimal(
                "20"
            ),
            actual_progress=Decimal(
                "21"
            ),
        )

    def test_dashboard_payload_calculates_part_progress(
        self,
    ):
        payload = (
            build_dashboard_payload(
                self.dashboard
            )
        )

        # 50% and 80% average = 65%
        self.assertEqual(
            payload["parts"][0][
                "progress"
            ],
            65,
        )

    def test_dashboard_payload_uses_latest_weekly_actual(
        self,
    ):
        payload = (
            build_dashboard_payload(
                self.dashboard
            )
        )

        self.assertEqual(
            payload["overall"][
                "percent"
            ],
            21,
        )

    def test_authenticated_user_can_view_dashboard(
        self,
    ):
        self.client.force_authenticate(
            user=self.normal_user
        )

        response = self.client.get(
            reverse(
                "project-dashboard-detail",
                kwargs={
                    "project_code": "k2p",
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_unauthenticated_user_cannot_view_dashboard(
        self,
    ):
        response = self.client.get(
            reverse(
                "project-dashboard-detail",
                kwargs={
                    "project_code": "k2p",
                },
            )
        )

        self.assertIn(
            response.status_code,
            (
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ),
        )

    def test_farmer_cannot_manage_dashboard(
        self,
    ):
        self.client.force_authenticate(
            user=self.normal_user
        )

        response = self.client.get(
            reverse(
                "project-dashboard-manage",
                kwargs={
                    "project_code": "k2p",
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_admin_can_manage_dashboard(
        self,
    ):
        self.client.force_authenticate(
            user=self.admin_user
        )

        response = self.client.get(
            reverse(
                "project-dashboard-manage",
                kwargs={
                    "project_code": "k2p",
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
