from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("django-admin/", admin.site.urls),  # optional raw DB admin (superusers only)
    path("", include("core.urls")),
]
