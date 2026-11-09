"""Routes des rêves."""

from django.urls import path

from dreams import views

app_name = "dreams"

urlpatterns = [
    path("nouveau/", views.record, name="record"),
    path("<uuid:dream_id>/", views.detail, name="detail"),
    path("<uuid:dream_id>/statut/", views.status, name="status"),
    path("fichiers/<path:path>", views.serve_file, name="file"),
]
