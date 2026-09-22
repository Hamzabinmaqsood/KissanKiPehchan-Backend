from django.urls import path

from .views import terms_and_conditions, community_usage_policy

urlpatterns = [

    path(
        "",
        terms_and_conditions,
        name="terms",
    ),

    path(
        "privacy-policy/",
        terms_and_conditions,
        name="privacy-policy",
    ),

    path(
        "community-policy/",
        community_usage_policy,
        name="community-usage-policy",
    ),

]