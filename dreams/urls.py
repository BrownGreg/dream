"""Routes des rêves."""

from django.urls import path

from dreams import views

app_name = "dreams"

urlpatterns = [
    path("fichiers/<path:path>", views.serve_file, name="file"),
]
