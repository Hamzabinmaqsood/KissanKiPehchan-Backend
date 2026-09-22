from django.urls import path
from .views import *

urlpatterns = [
    path("upload/", UploadQueryView.as_view(), name="upload_query"),
    path("respond/<int:query_id>/", SendResponseView.as_view(), name="send_response"),
    path("list/", QueryListView.as_view(), name="query_list"),
    path("respond/update/<int:response_id>/",UpdateResponseView.as_view(),name="update-response",),
    path("query-response/<int:query_id>/", MediaResponseByQueryAPIView.as_view(), name="query-response-list"),
    path("update/<int:query_id>/", UpdateQueryView.as_view(), name="update-query"),
]
