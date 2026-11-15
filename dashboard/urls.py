"""Routes du tableau de bord."""

from django.urls import path

from dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("statistiques/", views.stats, name="stats"),
    path("ops/", views.ops, name="ops"),
]
