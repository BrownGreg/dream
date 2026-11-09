"""Utilisateur identifié par e-mail et historique de ses consentements."""

from __future__ import annotations

from typing import Any, ClassVar

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager["User"]):
    """Crée des utilisateurs dont l'identifiant est l'adresse e-mail."""

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields: Any) -> User:
        if not email:
            raise ValueError("L'adresse e-mail est obligatoire.")
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields: Any) -> User:
        """Crée un utilisateur standard.

        Args:
            email: Adresse e-mail, normalisée en minuscules.
            password: Mot de passe en clair, haché avant enregistrement.
            **extra_fields: Autres champs du modèle.

        Returns:
            L'utilisateur enregistré.
        """
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields: Any) -> User:
        """Crée un administrateur (accès à ``/admin`` et ``/ops``).

        Args:
            email: Adresse e-mail.
            password: Mot de passe en clair.
            **extra_fields: Autres champs du modèle.

        Returns:
            L'administrateur enregistré.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Utilisateur de l'application ; l'e-mail remplace le nom d'utilisateur."""

    username = None  # type: ignore[assignment]
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = models.EmailField("adresse e-mail", unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    objects: ClassVar[UserManager] = UserManager()  # type: ignore[assignment]

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"

    def __str__(self) -> str:
        """Retourne l'adresse e-mail."""
        return self.email

    def has_consent(self, scope: str) -> bool:
        """Indique si le dernier choix de l'utilisateur pour ``scope`` est un accord.

        Args:
            scope: Une valeur de :class:`Consent.Scope`.

        Returns:
            ``True`` si la ligne la plus récente pour ce périmètre accorde le consentement.
        """
        latest = self.consents.filter(scope=scope).order_by("-created_at", "-id").first()
        return bool(latest and latest.granted)


class Consent(models.Model):
    """Un choix de consentement horodaté ; chaque changement crée une ligne (preuve RGPD).

    Les lignes ne sont jamais modifiées : l'état courant est la ligne la plus récente
    par périmètre (bloc 1, ``docs/preprod/specs/02_donnees.md``).
    """

    class Scope(models.TextChoices):
        PROCESSING = "processing", "Transcription et analyse du récit"
        IMAGE_GENERATION = "image_generation", "Envoi d'un prompt reformulé au générateur d'image"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="consents")
    scope = models.CharField(max_length=32, choices=Scope.choices)
    granted = models.BooleanField()
    text_version = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "consentement"
        indexes: ClassVar[list[models.Index]] = [models.Index(fields=["user", "scope", "-created_at"])]

    def __str__(self) -> str:
        """Résume le choix, sans donnée personnelle."""
        return f"{self.scope}={'oui' if self.granted else 'non'} ({self.text_version})"
