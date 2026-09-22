from django.urls import path
from .views import *

urlpatterns = [
      path("user/<int:user_id>/", UserReportsAPIView.as_view(), name="user-reports"),

    path("farmer/", generate_farmer_report, name="generate-farmer-report"),
    path("agro/", generate_agro_report, name="generate-agro-report"),

    # path("generate/", generate_report, name="generate-report"),
    path("farm-reports/<int:farm_id>/",FarmReportsAPIView.as_view(),name="farm-reports",),
]