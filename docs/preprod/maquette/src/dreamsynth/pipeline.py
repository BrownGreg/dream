"""Orchestration du traitement d'un rêve (version synchrone de la séquence des specs §3).

Garanties :
- aucun appel à un service sans le consentement correspondant (EXF-03) ;
- aucun appel au générateur d'image si l'utilisateur l'a refusé (EXF-11) ;
- l'émotion est inférée du texte uniquement (ENF-09) ;
- une panne de l'image n'empêche pas d'enregistrer le rêve (dégradation gracieuse).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from dreamsynth.audio import AudioUpload, validate_audio
from dreamsynth.domain.emotion import Emotion
from dreamsynth.domain.models import (
    AssetKind,
    ConsentScope,
    Dream,
    DreamStatus,
    EmotionAnalysis,
    EmotionSource,
    GeneratedAsset,
    Transcription,
)
from dreamsynth.errors import ContentRejectedError, DreamError, ErrorCode
from dreamsynth.services.dream_analysis import DreamAnalysis
from dreamsynth.services.ports import Services


class Step(StrEnum):
    """Étapes affichées dans l'indicateur de progression (EXF-10)."""

    VALIDATION = "Vérification de l'audio"
    TRANSCRIPTION = "Transcription"
    ANALYSIS = "Analyse du rêve"
    IMAGE = "Génération de l'image"
    AMBIANCE = "Choix de l'ambiance"


ProgressCallback = Callable[[Step], None]


@dataclass(frozen=True)
class GenerationOptions:
    """Choix de l'utilisateur qui conditionnent les appels aux services."""

    consents: frozenset[ConsentScope]
    image_disabled: bool = False
    style: str | None = None


@dataclass(frozen=True)
class DreamRequest:
    """Demande de traitement issue de l'UI : un audio et des options."""

    upload: AudioUpload
    options: GenerationOptions


@dataclass(frozen=True)
class ProcessResult:
    """Résultat d'un traitement : le rêve et, s'il y a lieu, le message à afficher."""

    dream: Dream
    message: str | None = None
    retryable: bool = False
    audio_retained: bool = False
    warnings: tuple[str, ...] = field(default=())

    @property
    def ok(self) -> bool:
        """Vrai si le rêve est enregistrable (statut `done`)."""
        return self.dream.status is DreamStatus.DONE


def _failed(dream: Dream, error: DreamError, audio_retained: bool) -> ProcessResult:
    failed = dream.model_copy(update={"status": DreamStatus.FAILED, "error": error.code.value})
    return ProcessResult(failed, error.user_message, error.retryable, audio_retained)


def process_dream(
    request: DreamRequest, services: Services, on_step: ProgressCallback | None = None
) -> ProcessResult:
    """Traite un audio de bout en bout.

    Args:
        request: audio, consentements et options de l'utilisateur.
        services: adapters injectés (mock ou réels).
        on_step: rappel appelé au début de chaque étape (indicateur de chargement).

    Returns:
        Le résultat ; en cas d'échec, `message` contient le texte à afficher et
        `audio_retained` indique si l'audio est conservé pour une relance.
    """
    notify = on_step or (lambda _step: None)
    options = request.options
    dream = Dream(image_disabled=options.image_disabled)
    if ConsentScope.TRANSCRIPTION not in options.consents:
        return _failed(dream, DreamError(ErrorCode.CONSENT_REQUIRED), audio_retained=False)

    notify(Step.VALIDATION)
    try:
        meta = validate_audio(request.upload)
    except DreamError as exc:
        return _failed(dream, exc, audio_retained=False)
    dream = dream.model_copy(update={"audio": meta})

    notify(Step.TRANSCRIPTION)
    try:
        result = services.transcriber.transcribe(request.upload.data, request.upload.filename)
    except DreamError as exc:
        return _failed(dream, exc, audio_retained=True)
    transcription = Transcription(text=result.text, provider=result.provider, model=result.model)
    dream = dream.model_copy(
        update={"transcription": transcription, "status": DreamStatus.TRANSCRIBED}
    )
    return _analyze_and_generate(dream, options, services, notify)


def regenerate_from_text(
    dream: Dream, text: str, options: GenerationOptions, services: Services
) -> ProcessResult:
    """Relance analyse et génération après correction de la transcription (US-05)."""
    if dream.transcription is None:
        raise ValueError("rêve sans transcription")
    edited = dream.transcription.model_copy(update={"text": text, "edited_by_user": True})
    base = dream.model_copy(
        update={
            "transcription": edited,
            "assets": (),
            "status": DreamStatus.TRANSCRIBED,
            "image_disabled": options.image_disabled,
        }
    )
    return _analyze_and_generate(base, options, services, lambda _step: None)


def _analyze_and_generate(
    dream: Dream, options: GenerationOptions, services: Services, notify: ProgressCallback
) -> ProcessResult:
    if dream.transcription is None:
        raise ValueError("analyse impossible sans transcription")
    notify(Step.ANALYSIS)
    try:
        analysis = services.analyzer.analyze(dream.transcription.text, options.style)
    except DreamError as exc:
        return _failed(dream, exc, audio_retained=False)
    dream = _apply_analysis(dream, analysis, options.consents)

    warnings: list[str] = []
    assets: list[GeneratedAsset] = []
    wants_image = not options.image_disabled and ConsentScope.IMAGE in options.consents
    if wants_image:
        notify(Step.IMAGE)
        try:
            image = services.image.generate(analysis.visual_prompt)
            assets.append(
                GeneratedAsset(
                    kind=AssetKind.IMAGE, uri=image.uri, provider=image.provider, model=image.model
                )
            )
        except ContentRejectedError as exc:
            warnings.append(exc.user_message)
        except DreamError:
            warnings.append(DreamError(ErrorCode.IMAGE_UNAVAILABLE).user_message)

    notify(Step.AMBIANCE)
    assets.append(
        GeneratedAsset(
            kind=AssetKind.AMBIANCE,
            uri=services.ambiance.for_emotion(analysis.emotion),
            provider="bibliotheque",
            model="cc0-loops",
        )
    )
    done = dream.model_copy(
        update={"assets": tuple(assets), "status": DreamStatus.DONE, "error": None}
    )
    return ProcessResult(done, warnings[0] if warnings else None, warnings=tuple(warnings))


def _apply_analysis(
    dream: Dream, analysis: DreamAnalysis, consents: frozenset[ConsentScope]
) -> Dream:
    emotion = (
        EmotionAnalysis(emotion=analysis.emotion, confidence=analysis.confidence)
        if ConsentScope.EMOTION_TRACKING in consents
        else None
    )
    return dream.model_copy(
        update={
            "title": analysis.title,
            "visual_prompt": analysis.visual_prompt,
            "emotion": emotion,
            "status": DreamStatus.ANALYZED,
        }
    )


def correct_emotion(dream: Dream, emotion: Emotion) -> Dream:
    """Remplace l'émotion par le choix de l'utilisateur (US-14)."""
    return dream.model_copy(
        update={"emotion": EmotionAnalysis(emotion=emotion, source=EmotionSource.USER)}
    )
