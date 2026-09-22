from django.shortcuts import render
from django.shortcuts import (
    get_object_or_404,
)
from django.contrib.auth import get_user_model

from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework import status
from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.response import (
    Response,
)
from rest_framework.views import APIView

from .models import ProjectDashboard
from .permissions import (
    IsDashboardEditor,
)
from .serializers import (
    DashboardPayloadSerializer,
)
from .services import (
    build_dashboard_payload,
    update_dashboard_from_payload,
)


DEFAULT_PROJECT_CODE = "k2p"


def get_dashboard(
    project_code,
):
    return get_object_or_404(
        ProjectDashboard,
        project_code=project_code,
        is_active=True,
    )


class ProjectDashboardAPIView(
    APIView
):
    """
    Read-only live dashboard endpoint.

    All calculations are performed by the backend.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    def get(
        self,
        request,
        project_code=DEFAULT_PROJECT_CODE,
    ):
        dashboard = get_dashboard(
            project_code
        )

        return Response(
            build_dashboard_payload(
                dashboard
            ),
            status=status.HTTP_200_OK,
        )


class ProjectDashboardManageAPIView(
    APIView
):
    """
    Editor endpoint.

    GET:
        Load the current live dashboard.

    PUT:
        Replace/update the dashboard using the same JSON shape
        already understood by editor.html.
    """

    permission_classes = [
        IsAuthenticated,
        IsDashboardEditor,
    ]

    def get(
        self,
        request,
        project_code=DEFAULT_PROJECT_CODE,
    ):
        dashboard = get_dashboard(
            project_code
        )

        return Response(
            build_dashboard_payload(
                dashboard
            ),
            status=status.HTTP_200_OK,
        )

    def put(
        self,
        request,
        project_code=DEFAULT_PROJECT_CODE,
    ):
        dashboard = get_dashboard(
            project_code
        )

        serializer = (
            DashboardPayloadSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        dashboard = (
            update_dashboard_from_payload(
                dashboard,
                serializer.validated_data,
                user=request.user,
            )
        )

        return Response(
            {
                "status": "success",
                "message": (
                    "Project dashboard updated successfully."
                ),
                "data": (
                    build_dashboard_payload(
                        dashboard
                    )
                ),
            },
            status=status.HTTP_200_OK,
        )

class DashboardLoginAPIView(APIView):
    """
    Dedicated login for the LIMS Project Dashboard.

    Uses username + password instead of the normal
    mobile-number login used by the main application.
    """

    permission_classes = []

    def post(self, request):
        username = str(
            request.data.get("username", "")
        ).strip()

        password = str(
            request.data.get("password", "")
        )

        if not username or not password:
            return Response(
                {
                    "detail": (
                        "Username and password are required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        User = get_user_model()

        try:
            user = User.objects.select_related(
                "role"
            ).get(
                username__iexact=username,
                is_active=True,
            )

        except User.DoesNotExist:
            return Response(
                {
                    "detail": (
                        "Invalid username or password."
                    )
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(password):
            return Response(
                {
                    "detail": (
                        "Invalid username or password."
                    )
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        allowed_usernames = {
            "admin",
            "ceo",
            "guest",
        }

        if user.username.lower() not in allowed_usernames:
            return Response(
                {
                    "detail": (
                        "This account does not have "
                        "dashboard login access."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)

        role_name = ""

        if getattr(user, "role", None):
            role_name = user.role.name

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user_id": user.id,
                "user_name": user.username,
                "user_role": role_name,
            },
            status=status.HTTP_200_OK,
        )

# ==========================================================
# FRONTEND PAGE VIEWS
# ==========================================================

def project_dashboard_page(request):
    """
    Render the live LIMS/K2P project dashboard frontend.
    Authentication is handled by the JWT-based auth.js.
    """
    return render(
        request,
        "limsdaehboard/dashboard.html",
    )


def project_dashboard_editor_page(request):
    """
    Render the dashboard editor frontend.

    Actual edit authorization is enforced again by the
    /api/project-dashboard/k2p/manage/ backend API.
    """
    return render(
        request,
        "limsdaehboard/editor.html",
    )
