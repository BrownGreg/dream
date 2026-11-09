"""Pipeline d'un rêve : transcription → émotion → prompt visuel → image.

Exécuté par le worker (``dreams.tasks``), jamais dans une requête HTTP. Chaque étape
vérifie d'abord si son résultat existe déjà : rejouer la tâche après un plantage
reprend à l'étape manquante sans refaire (ni repayer) ce qui a réussi. Un échec de
l'image n'efface rien : le rêve passe en ``partial`` avec sa transcription et son émotion.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import structlog
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from accounts.models import Consent
from dreams import audio
from dreams.locks import dream_lock
from dreams.models import Dream, EmotionAnalysis, GeneratedAsset, Transcription
from dreams.services import registry
from dreams.services.errors import AIServiceError, BudgetExceededError, ProviderError, SafetyRejectionError
from dreams.services.ports import AudioInput, Caller

log = structlog.get_logger(__name__)


class StepFailedError(Exception):
    """Étape bloquante en échec : le rêve passe en ``failed`` avec ``code``."""

    def __init__(self, code: str) -> None:
        """Construit l'erreur.

        Args:
            code: Code d'erreur affichable (``dreams.messages``).
        """
        super().__init__(code)
        self.code = code


def _set_status(dream: Dream, status: str, error_code: str = "") -> None:
    dream.status = status
    dream.error_code = error_code
    dream.save(update_fields=["status", "error_code", "updated_at"])


def purge_audio(dream: Dream) -> None:
    """Supprime l'enregistrement d'un rêve et note la date de suppression.

    Args:
        dream: Rêve dont l'audio doit disparaître.
    """
    if dream.audio:
        dream.audio.delete(save=False)
    dream.audio = ""
    dream.audio_purged_at = timezone.now()
    dream.save(update_fields=["audio", "audio_purged_at", "updated_at"])


def purge_stale_audio(max_age: timedelta = timedelta(hours=24)) -> int:
    """Supprime les enregistrements restés plus de 24 h (transcription jamais réussie).

    Args:
        max_age: Âge maximal d'un audio conservé (bloc 1 : 24 h).

    Returns:
        Le nombre d'enregistrements supprimés.
    """
    stale = Dream.objects.filter(audio_purged_at__isnull=True, created_at__lt=timezone.now() - max_age).exclude(
        audio=""
    )
    count = 0
    for dream in stale:
        purge_audio(dream)
        count += 1
    return count


def _transcribe(dream: Dream, caller: Caller) -> Transcription:
    existing = Transcription.objects.filter(dream=dream).first()
    if existing:
        return existing
    _set_status(dream, Dream.Status.TRANSCRIBING)
    if not dream.audio:
        raise StepFailedError("audio_missing")
    with dream.audio.open("rb") as handle:
        raw = handle.read()
    try:
        mp3 = audio.to_mp3(raw)
    except audio.AudioError as exc:
        raise StepFailedError(exc.code) from exc
    duration = dream.audio_duration_s or Decimal(0)
    try:
        transcript = registry.transcriber().transcribe(AudioInput(mp3, duration), caller)
    except ProviderError as exc:
        raise StepFailedError("transcription_empty" if "vide" in str(exc) else exc.code) from exc
    except AIServiceError as exc:
        raise StepFailedError(exc.code) from exc
    with transaction.atomic():
        transcription = Transcription.objects.create(
            dream=dream, text=transcript.text, provider=transcript.provider, model=transcript.model
        )
        # Transcription réussie : l'audio n'a plus de raison d'être conservé (bloc 1, RGPD).
        purge_audio(dream)
    return transcription


def _classify(dream: Dream, text: str, caller: Caller) -> EmotionAnalysis:
    current = dream.current_emotion
    if current:
        return current
    _set_status(dream, Dream.Status.ANALYZING)
    result = registry.emotion_classifier().classify(text, caller)
    return EmotionAnalysis.objects.create(
        dream=dream,
        emotion=result.emotion,
        confidence=result.confidence,
        provider=result.provider,
        source=EmotionAnalysis.Source.MODEL,
    )


def _image_skip_reason(dream: Dream) -> str:
    if dream.image_disabled:
        return "image_disabled"
    if not dream.user.has_consent(Consent.Scope.IMAGE_GENERATION):
        return "image_no_consent"
    return ""


def generate_image(dream: Dream, text: str, emotion: str, caller: Caller) -> GeneratedAsset:
    """Rédige le prompt et génère l'image ; un refus de sécurité donne une seule reformulation.

    Utilisée par le pipeline et par la régénération (US-07). N'échoue jamais : le résultat,
    réussi ou non, est enregistré comme une tentative.

    Args:
        dream: Rêve concerné.
        text: Transcription.
        emotion: Émotion retenue.
        caller: Contexte de journalisation.

    Returns:
        La tentative enregistrée (``ok``, ``rejected`` ou ``failed``).
    """
    attempt = (dream.assets.filter(kind=GeneratedAsset.Kind.IMAGE).count()) + 1
    asset = GeneratedAsset(dream=dream, kind=GeneratedAsset.Kind.IMAGE, attempt=attempt)
    if attempt > settings.AI_MAX_IMAGE_ATTEMPTS:
        asset.status, asset.rejection_reason = GeneratedAsset.Status.FAILED, "image_attempts"
        return asset  # pas enregistrée : la contrainte d'unicité borne déjà les tentatives
    try:
        visual = registry.prompt_builder().build(text, emotion, caller)
        if not dream.title:
            dream.title = visual.title
            dream.save(update_fields=["title", "updated_at"])
        asset.visual_prompt = visual.prompt
        try:
            image = registry.image_generator().generate(visual.prompt, caller)
        except SafetyRejectionError:
            log.info("image_rejected_retry_softer", dream_id=str(dream.id))
            visual = registry.prompt_builder().build(text, emotion, caller, softer=True)
            asset.visual_prompt = visual.prompt
            image = registry.image_generator().generate(visual.prompt, caller)
    except SafetyRejectionError:
        asset.status, asset.rejection_reason = GeneratedAsset.Status.REJECTED, "image_rejected"
    except BudgetExceededError:
        asset.status, asset.rejection_reason = GeneratedAsset.Status.FAILED, "image_budget"
    except AIServiceError:
        asset.status, asset.rejection_reason = GeneratedAsset.Status.FAILED, "image_failed"
    else:
        asset.status = GeneratedAsset.Status.OK
        asset.provider, asset.model = image.provider, image.model
        asset.file.save(f"image.{image.extension}", ContentFile(image.data), save=False)
    asset.save()
    return asset


def _image(dream: Dream, text: str, emotion: str, caller: Caller) -> bool:
    """Étape image ; retourne ``True`` si le rêve est complet, ``False`` s'il est partiel."""
    if dream.current_image or dream.assets.filter(kind=GeneratedAsset.Kind.IMAGE).exists():
        # Une tentative existe déjà (réussie ou non) : la reprise ne relance pas une image payante.
        return dream.current_image is not None
    reason = _image_skip_reason(dream)
    if reason:
        GeneratedAsset.objects.create(
            dream=dream, kind=GeneratedAsset.Kind.IMAGE, status=GeneratedAsset.Status.SKIPPED, rejection_reason=reason
        )
        return True
    _set_status(dream, Dream.Status.GENERATING)
    return generate_image(dream, text, emotion, caller).status == GeneratedAsset.Status.OK


def run(dream_id: UUID) -> str:
    """Traite un rêve de bout en bout ; idempotent.

    Args:
        dream_id: Rêve à traiter.

    Returns:
        Le statut final (ou ``skipped`` si le rêve est absent, terminé ou déjà en cours).
    """
    purge_stale_audio()
    dream = Dream.objects.select_related("user").filter(id=dream_id).first()
    if dream is None or dream.status in (Dream.Status.DONE, Dream.Status.PARTIAL):
        return "skipped"
    with dream_lock(dream.id) as acquired:
        if not acquired:
            log.info("dream_already_processing", dream_id=str(dream.id))
            return "skipped"
        caller = Caller(dream_id=dream.id, user_id=dream.user_id)
        bound = log.bind(dream_id=str(dream.id))
        try:
            transcription = _transcribe(dream, caller)
            emotion = _classify(dream, transcription.text, caller)
            complete = _image(dream, transcription.text, emotion.emotion, caller)
        except StepFailedError as exc:
            bound.warning("dream_failed", error=exc.code)
            _set_status(dream, Dream.Status.FAILED, exc.code)
            return Dream.Status.FAILED
        except Exception:
            # Aucune exception ne doit laisser un rêve « en cours » pour toujours.
            bound.exception("dream_crashed")
            _set_status(dream, Dream.Status.FAILED, "internal_error")
            raise
        final = Dream.Status.DONE if complete else Dream.Status.PARTIAL
        _set_status(dream, final)
        bound.info("dream_processed", status=final)
        return final


def regenerate(dream_id: UUID) -> str:
    """Nouvelle tentative d'image pour un rêve terminé.

    Args:
        dream_id: Rêve concerné.

    Returns:
        Le statut de la tentative, ou ``skipped`` si le rêve n'est pas prêt.
    """
    dream = Dream.objects.select_related("user").filter(id=dream_id).first()
    if dream is None or not hasattr(dream, "transcription"):
        return "skipped"
    with dream_lock(dream.id) as acquired:
        if not acquired:
            return "skipped"
        emotion = dream.current_emotion
        caller = Caller(dream_id=dream.id, user_id=dream.user_id)
        _set_status(dream, Dream.Status.GENERATING)
        asset = generate_image(dream, dream.transcription.text, emotion.emotion if emotion else "neutre", caller)
        has_image = dream.current_image is not None
        _set_status(dream, Dream.Status.DONE if has_image else Dream.Status.PARTIAL)
        return asset.status
