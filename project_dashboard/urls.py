from django.urls import path
from .views import (
    DashboardLoginAPIView,
    ProjectDashboardAPIView,
    ProjectDashboardManageAPIView,
)

from .views import (
    ProjectDashboardAPIView,
    ProjectDashboardManageAPIView,
    DashboardLoginAPIView,
)


urlpatterns = [
    # Default K2P dashboard
    path(
        "",
        ProjectDashboardAPIView.as_view(),
        name="project-dashboard",
    ),

    path(
    "login/",
    DashboardLoginAPIView.as_view(),
    name="project-dashboard-login",
),

    # Explicit project dashboard
    path(
        "<slug:project_code>/",
        ProjectDashboardAPIView.as_view(),
        name="project-dashboard-detail",
    ),

    # Default K2P editor API
    path(
        "manage/default/",
        ProjectDashboardManageAPIView.as_view(),
        name="project-dashboard-manage-default",
    ),

    # Explicit project editor API
    path(
        "<slug:project_code>/manage/",
        ProjectDashboardManageAPIView.as_view(),
        name="project-dashboard-manage",
    ),
]
