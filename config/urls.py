"""Routes racines du projet."""

from django.contrib import admin
from django.urls import include, path

from config import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("admin/", admin.site.urls),
    path("comptes/", include("accounts.urls")),
    path("", include("dashboard.urls")),
]
