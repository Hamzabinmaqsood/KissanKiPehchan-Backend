
from .admin_export import export_full_database
from project_dashboard.views import (
    project_dashboard_page,
    project_dashboard_editor_page,
)
from django.contrib import admin
from django.urls import path,include
from django.conf.urls.static import static
from django.conf import settings
from .views import *
urlpatterns = [
    path("api/admin/export-db/",export_full_database,name="admin-export-db",),
    path('api/admin/', admin.site.urls),
    path('api/voice_api/', include('voice_api.urls')),
    path("api/query/", include("querry.urls")),
    path("api/community/", include("community.urls")),
    path("api/mandi/", include("mandi.urls")),
    path("api/user/", include("User.urls")),
    path("api/cr/", include("CropsRecomendations.urls")),
    path("api/report/", include("Reports.urls")),
    path("api/values/", include("LinkedValues.urls")),


    path("api/dashboard/", DashboardAPIView.as_view(), name="dashboard"),
    path("api/faqs/", include("faq.urls")),
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('api/verify-token/', TokenVerificationView.as_view(), name='token_verification'),
    path('api/mark-kml/', show_kml_page),
    path('api/generate-indices/', generate_indices_report),
    path("api/terms/", include("terms.urls"),),
    path("api/project-dashboard/",include("project_dashboard.urls"),),
    path(
    "api/lims-dashboard/",
    project_dashboard_page,
    name="project-dashboard-page",
    ),

    path(
        "api/lims-dashboard/editor/",
        project_dashboard_editor_page,
        name="project-dashboard-editor-page",
    ),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
