"""Administration des comptes ; le contenu des rêves n'y est jamais exposé."""

from typing import ClassVar

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from accounts.models import Consent, User


class ConsentInline(admin.TabularInline[Consent, User]):
    """Historique des consentements, en lecture seule (preuve)."""

    model = Consent
    extra = 0
    can_delete = False
    readonly_fields = ("scope", "granted", "text_version", "created_at")


@admin.register(User)
class UserAdmin(BaseUserAdmin[User]):
    """Gestion des utilisateurs par e-mail."""

    ordering = ("email",)
    list_display = ("email", "is_staff", "is_active", "date_joined")
    search_fields = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Droits", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)
    inlines: ClassVar[list[type[admin.options.InlineModelAdmin]]] = [ConsentInline]  # type: ignore[type-arg]
