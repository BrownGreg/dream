"""Routes des rêves."""

from django.urls import path

from dreams import views

app_name = "dreams"

urlpatterns = [
    path("nouveau/", views.record, name="record"),
    path("<uuid:dream_id>/", views.detail, name="detail"),
    path("<uuid:dream_id>/statut/", views.status, name="status"),
    path("<uuid:dream_id>/transcription/", views.edit_transcription, name="edit_transcription"),
    path("<uuid:dream_id>/emotion/", views.edit_emotion, name="edit_emotion"),
    path("<uuid:dream_id>/regenerer/", views.regenerate, name="regenerate"),
    path("<uuid:dream_id>/supprimer/", views.delete, name="delete"),
    path("fichiers/<path:path>", views.serve_file, name="file"),
]
