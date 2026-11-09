"""Modèle de données des rêves, aligné sur l'ERD du bloc 1.

Écarts avec ``docs/preprod/specs/02_donnees.md`` (documentés dans ``docs/specs/donnees.md``) :
l'audio est un champ du rêve plutôt qu'une table ``audio_assets`` (un seul fichier par rêve,
supprimé après transcription) ; ``generations`` et ``generation_assets`` sont fusionnées en
``GeneratedAsset`` (un fichier au plus par génération).
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import ClassVar

from django.conf import settings
from django.db import models
from django.db.models import Q

from dreams.emotions import Emotion
from dreams.fields import EncryptedTextField


def _audio_path(instance: Dream, filename: str) -> str:
    # Nom aléatoire : jamais le nom de fichier d'origine (il peut contenir une donnée personnelle).
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"audio/{instance.id}/{uuid.uuid4().hex}.{extension}"


def _asset_path(instance: GeneratedAsset, filename: str) -> str:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"assets/{instance.dream_id}/{instance.kind}-{uuid.uuid4().hex}.{extension}"


class Dream(models.Model):
    """Un rêve raconté par un utilisateur, et l'état de son traitement."""

    class Status(models.TextChoices):
        RECEIVED = "received", "Reçu"
        TRANSCRIBING = "transcribing", "Transcription"
        ANALYZING = "analyzing", "Analyse"
        GENERATING = "generating", "Création de l'image"
        DONE = "done", "Terminé"
        PARTIAL = "partial", "Terminé en partie"
        FAILED = "failed", "Échec"

    TERMINAL_STATUSES: ClassVar[frozenset[str]] = frozenset({Status.DONE, Status.PARTIAL, Status.FAILED})

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dreams")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RECEIVED)
    error_code = models.CharField(max_length=40, blank=True)
    title = EncryptedTextField(blank=True)
    image_disabled = models.BooleanField(default=False)

    audio = models.FileField(upload_to=_audio_path, blank=True)
    audio_mime = models.CharField(max_length=40, blank=True)
    audio_duration_s = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    audio_size_bytes = models.PositiveIntegerField(null=True, blank=True)
    audio_purged_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "rêve"
        ordering = ("-created_at",)
        indexes: ClassVar[list[models.Index]] = [models.Index(fields=["user", "-created_at"])]

    def __str__(self) -> str:
        """Identifie le rêve sans en révéler le contenu."""
        return f"Rêve {self.id} ({self.status})"

    @property
    def is_finished(self) -> bool:
        """Indique si le traitement est arrivé à un état final."""
        return self.status in self.TERMINAL_STATUSES

    @property
    def current_emotion(self) -> EmotionAnalysis | None:
        """Émotion retenue (la plus récente, modèle ou correction de l'utilisateur)."""
        return self.emotions.filter(is_current=True).first()

    @property
    def current_image(self) -> GeneratedAsset | None:
        """Dernière image générée avec succès."""
        return (
            self.assets.filter(kind=GeneratedAsset.Kind.IMAGE, status=GeneratedAsset.Status.OK)
            .order_by("-attempt")
            .first()
        )


class Transcription(models.Model):
    """Texte transcrit d'un rêve, chiffré en base, modifiable par l'utilisateur (US-05)."""

    dream = models.OneToOneField(Dream, on_delete=models.CASCADE, related_name="transcription")
    text = EncryptedTextField()
    provider = models.CharField(max_length=40)
    model = models.CharField(max_length=80)
    language = models.CharField(max_length=8, default="fr")
    edited_by_user = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        """Résumé technique, sans le texte."""
        return f"Transcription de {self.dream_id} ({self.provider})"


class EmotionAnalysis(models.Model):
    """Émotion d'un rêve ; une ligne par proposition ou correction, une seule courante."""

    class Source(models.TextChoices):
        MODEL = "model", "Modèle"
        USER = "user", "Utilisateur"

    dream = models.ForeignKey(Dream, on_delete=models.CASCADE, related_name="emotions")
    emotion = models.CharField(max_length=16, choices=Emotion.choices)
    confidence = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    source = models.CharField(max_length=8, choices=Source.choices, default=Source.MODEL)
    provider = models.CharField(max_length=40, blank=True)
    is_current = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "analyse d'émotion"
        verbose_name_plural = "analyses d'émotion"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(fields=["dream"], condition=Q(is_current=True), name="une_emotion_courante"),
            models.CheckConstraint(
                condition=Q(confidence__isnull=True) | Q(confidence__gte=0, confidence__lte=1),
                name="confiance_entre_0_et_1",
            ),
        ]

    def __str__(self) -> str:
        """Émotion et source."""
        return f"{self.emotion} ({self.source})"


class GeneratedAsset(models.Model):
    """Contenu généré pour un rêve (image, ambiance), copié dans notre stockage."""

    class Kind(models.TextChoices):
        IMAGE = "image", "Image"
        AMBIANCE = "ambiance", "Ambiance sonore"

    class Status(models.TextChoices):
        OK = "ok", "Généré"
        SKIPPED = "skipped", "Non demandé"
        REJECTED = "rejected", "Refusé par le filtre de sécurité"
        FAILED = "failed", "Échec"

    dream = models.ForeignKey(Dream, on_delete=models.CASCADE, related_name="assets")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    status = models.CharField(max_length=10, choices=Status.choices)
    attempt = models.PositiveSmallIntegerField(default=1)
    visual_prompt = EncryptedTextField(blank=True)
    file = models.FileField(upload_to=_asset_path, blank=True)
    provider = models.CharField(max_length=40, blank=True)
    model = models.CharField(max_length=80, blank=True)
    rejection_reason = models.CharField(max_length=40, blank=True)
    # Toujours vrai : mention « générée par IA » (AI Act, art. 50).
    ai_generated = models.BooleanField(default=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "contenu généré"
        verbose_name_plural = "contenus générés"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(fields=["dream", "kind", "attempt"], name="une_generation_par_tentative"),
        ]

    def __str__(self) -> str:
        """Type, tentative et statut."""
        return f"{self.kind} #{self.attempt} ({self.status})"


class ApiCall(models.Model):
    """Journal de chaque appel à un fournisseur d'IA : coût, latence, issue (ADR-009).

    Conservé sans contenu ; ``dream`` passe à ``NULL`` quand le rêve est supprimé
    pour garder la trace du coût.
    """

    class Step(models.TextChoices):
        STT = "stt", "Transcription"
        EMOTION = "emotion", "Émotion"
        PROMPT = "prompt", "Prompt visuel"
        IMAGE = "image", "Image"
        SOUND = "sound", "Son"

    class Outcome(models.TextChoices):
        OK = "ok", "Succès"
        ERROR = "error", "Erreur"
        TIMEOUT = "timeout", "Délai dépassé"
        REJECTED = "rejected", "Refus de sécurité"
        BLOCKED = "blocked", "Bloqué par le budget"

    id = models.BigAutoField(primary_key=True)
    dream = models.ForeignKey(Dream, on_delete=models.SET_NULL, null=True, blank=True, related_name="api_calls")
    user_pseudonym = models.CharField(max_length=64, blank=True, db_index=True)
    step = models.CharField(max_length=10, choices=Step.choices)
    provider = models.CharField(max_length=40)
    model = models.CharField(max_length=80)
    outcome = models.CharField(max_length=10, choices=Outcome.choices)
    http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    error_type = models.CharField(max_length=60, blank=True)
    attempt = models.PositiveSmallIntegerField(default=1)
    latency_ms = models.PositiveIntegerField(default=0)
    billed_units = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal(0))
    unit = models.CharField(max_length=16, blank=True)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=Decimal(0))
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "appel API"
        verbose_name_plural = "appels API"
        ordering = ("-created_at",)
        indexes: ClassVar[list[models.Index]] = [models.Index(fields=["provider", "step", "-created_at"])]

    def __str__(self) -> str:
        """Résumé technique de l'appel."""
        return f"{self.step}/{self.provider} {self.outcome} {self.latency_ms} ms"
