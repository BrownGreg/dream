"""Champ texte chiffré au niveau applicatif (bloc 1, specs §2).

Le contenu des rêves est une donnée potentiellement sensible (RGPD art. 9) : il est
chiffré avant d'atteindre la base, avec une clé qui n'y est jamais stockée
(``FIELD_ENCRYPTION_KEYS``). Plusieurs clés permettent la rotation : la première
chiffre, toutes déchiffrent.
"""

from functools import cache
from typing import Any

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.backends.base.base import BaseDatabaseWrapper


@cache
def _fernet() -> MultiFernet:
    keys = settings.FIELD_ENCRYPTION_KEYS
    if not keys:
        raise ImproperlyConfigured("FIELD_ENCRYPTION_KEYS est vide : impossible de chiffrer le contenu des rêves.")
    return MultiFernet([Fernet(key) for key in keys])


def encrypt(value: str) -> str:
    """Chiffre une chaîne.

    Args:
        value: Texte en clair.

    Returns:
        Jeton Fernet (base64 URL-safe) contenant le texte chiffré et authentifié.
    """
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    """Déchiffre un jeton produit par :func:`encrypt`.

    Args:
        token: Jeton Fernet.

    Returns:
        Le texte en clair.

    Raises:
        InvalidToken: Si le jeton a été altéré ou chiffré avec une clé inconnue.
    """
    return _fernet().decrypt(token.encode()).decode()


class EncryptedTextField(models.TextField[str, str]):
    """``TextField`` chiffré : non filtrable ni triable en base, par construction."""

    def get_prep_value(self, value: Any) -> Any:
        """Chiffre la valeur avant écriture."""
        value = super().get_prep_value(value)
        if value is None or value == "":
            return value
        return encrypt(str(value))

    def from_db_value(self, value: str | None, expression: Any, connection: BaseDatabaseWrapper) -> str | None:
        """Déchiffre la valeur lue en base."""
        if value is None or value == "":
            return value
        try:
            return decrypt(value)
        except InvalidToken as exc:
            raise ImproperlyConfigured(
                "Contenu chiffré illisible : clé FIELD_ENCRYPTION_KEYS absente ou erronée."
            ) from exc
