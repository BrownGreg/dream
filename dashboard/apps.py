"""Configuration de l'application ``dashboard``."""

from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """Historique, filtres, statistiques et page ``/ops``."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "dashboard"
    verbose_name = "Tableau de bord"
