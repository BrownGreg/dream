"""Configuration de l'application ``accounts``."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Comptes, authentification et consentements RGPD."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Comptes"
