from django.shortcuts import render


def terms_and_conditions(request):

    return render(
        request,
        "terms/terms_and_conditions.html"
    )


def community_usage_policy(request):

    return render(
        request,
        "terms/community_usage_policy.html"
    )