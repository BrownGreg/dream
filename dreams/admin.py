"""Administration : métadonnées techniques uniquement, jamais le contenu des rêves."""

from typing import ClassVar

from django.contrib import admin
from django.http import HttpRequest

from dreams.models import ApiCall, Dream


@admin.register(Dream)
class DreamAdmin(admin.ModelAdmin[Dream]):
    """Suivi des traitements ; titre, transcription et prompts ne sont pas affichés."""

    list_display = ("id", "status", "error_code", "image_disabled", "created_at")
    list_filter = ("status", "error_code")
    fields = ("id", "user", "status", "error_code", "image_disabled", "audio_purged_at", "created_at", "updated_at")
    readonly_fields: ClassVar[list[str]] = [
        "id",
        "user",
        "status",
        "error_code",
        "image_disabled",
        "audio_purged_at",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Un rêve naît d'un enregistrement, jamais de l'administration."""
        return False


@admin.register(ApiCall)
class ApiCallAdmin(admin.ModelAdmin[ApiCall]):
    """Journal des appels API en lecture seule (preuve du budget)."""

    list_display = ("created_at", "step", "provider", "model", "outcome", "http_status", "latency_ms", "cost_usd")
    list_filter = ("step", "provider", "outcome")
    date_hierarchy = "created_at"

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Journal en écriture seule par le code."""
        return False

    def has_change_permission(self, request: HttpRequest, obj: ApiCall | None = None) -> bool:
        """Journal non modifiable."""
        return False
