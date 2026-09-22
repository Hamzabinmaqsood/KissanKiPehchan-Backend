from datetime import date, datetime, time

from django.utils import timezone
from django.utils.dateparse import parse_date

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import MandiDailyData
from .fetcher import fetch_and_save_mandi


class MandiDataView(APIView):

    permission_classes = [IsAuthenticated]

    UPDATE_HOUR = 10  # 10 AM

    def format_response(self, source, obj):
        return Response({
            "source": source,
            "date": str(obj.date),
            "cached_at": obj.updated_at,
            "data": obj.data
        }, status=status.HTTP_200_OK)

    def should_refresh_cache(self, obj):
        now = timezone.localtime()
        today_10am = timezone.make_aware(
            datetime.combine(
                now.date(),
                time(hour=self.UPDATE_HOUR)
            )
        )
        if now < today_10am:
            return False
        last_updated = timezone.localtime(obj.updated_at)
        return last_updated < today_10am

    def post(self, request):
        qdate_str = request.data.get("date")
        if not qdate_str:
            return Response(
                {"error": "date is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        req_date = parse_date(qdate_str)

        if not req_date:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if req_date > date.today():
            return Response(
                {"error": "Future date not allowed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        obj = MandiDailyData.objects.filter(date=req_date).first()

        if obj:
            if req_date == date.today() and self.should_refresh_cache(obj):

                try:
                    fetch_and_save_mandi(req_date)
                    obj = MandiDailyData.objects.get(date=req_date)
                    return self.format_response(
                        "cache_refreshed_after_10am",
                        obj
                    )

                except Exception:
                    return self.format_response(
                        "database_cache_api_failed",
                        obj
                    )
            return self.format_response(
                "database_cache",
                obj
            )
        try:

            fetch_and_save_mandi(req_date)
            obj = MandiDailyData.objects.filter(date=req_date).first()
            if obj:
                return self.format_response(
                    "api_fetched_and_cached",
                    obj
                )
        except Exception as e:
            latest_obj = MandiDailyData.objects.order_by("-date").first()
            if latest_obj:
                return Response({
                    "source": "latest_backup_cache",
                    "requested_date": str(req_date),
                    "backup_date": str(latest_obj.date),
                    "error": "Live API fetch failed",
                    "details": str(e),
                    "data": latest_obj.data
                }, status=status.HTTP_200_OK)
            return Response({
                "error": "Failed to fetch mandi data",
                "details": str(e),
                "message": "No cached data available"
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)