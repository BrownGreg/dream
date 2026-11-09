"""Modèles du domaine : source unique du schéma `docs/schemas/dream.schema.json`.

Le schéma JSON est généré depuis ces classes (`python tools/export_schema.py`) ; il ne
doit jamais être édité à la main.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from dreamsynth.domain.emotion import Emotion

SCHEMA_VERSION: Literal["1.0.0"] = "1.0.0"


def _now() -> datetime:
    return datetime.now(UTC)


class ConsentScope(StrEnum):
    """Finalités consenties séparément (art. 9.2.a RGPD, section 5.1)."""

    TRANSCRIPTION = "transcription"
    IMAGE = "image_generation"
    EMOTION_TRACKING = "emotion_tracking"


class DreamStatus(StrEnum):
    """Étapes du traitement d'un rêve (diagramme de séquence)."""

    RECEIVED = "received"
    TRANSCRIBED = "transcribed"
    ANALYZED = "analyzed"
    DONE = "done"
    FAILED = "failed"


class EmotionSource(StrEnum):
    """Origine de l'émotion retenue (US-14)."""

    MODEL = "model"
    USER = "user"


class AssetKind(StrEnum):
    """Type de contenu généré rattaché à un rêve."""

    IMAGE = "image"
    AMBIANCE = "ambiance"
    SPEECH = "speech"
    VIDEO = "video"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AudioMeta(_Frozen):
    """Métadonnées de l'audio reçu ; le contenu audio n'est jamais conservé (section 5.6)."""

    filename: str = Field(max_length=255)
    mime_type: Literal["audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3"]
    duration_s: float = Field(gt=0, le=300)
    size_bytes: int = Field(gt=0, le=20 * 1024 * 1024)


class Transcription(_Frozen):
    """Texte transcrit du récit."""

    text: str = Field(min_length=1, max_length=20_000)
    language: str = Field(default="fr", pattern=r"^[a-z]{2}$")
    provider: str
    model: str
    edited_by_user: bool = False


class EmotionAnalysis(_Frozen):
    """Émotion dominante, inférée du texte (ADR-001) ou corrigée par l'utilisateur."""

    emotion: Emotion
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source: EmotionSource = EmotionSource.MODEL


class GeneratedAsset(_Frozen):
    """Contenu produit par IA ; porte toujours le marquage art. 50 AI Act."""

    kind: AssetKind
    uri: str = Field(description="URI dans notre stockage objet (jamais une URL fournisseur)")
    provider: str
    model: str
    ai_generated: Literal[True] = True
    created_at: datetime = Field(default_factory=_now)


class Dream(_Frozen):
    """Un rêve stocké, tel qu'exporté pour la portabilité (US-15)."""

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=_now)
    status: DreamStatus = DreamStatus.RECEIVED
    title: str | None = Field(default=None, max_length=80)
    audio: AudioMeta | None = None
    transcription: Transcription | None = None
    emotion: EmotionAnalysis | None = None
    visual_prompt: str | None = Field(default=None, max_length=1200)
    image_disabled: bool = Field(default=False, description="« Ne pas générer d'image » (US-11)")
    assets: tuple[GeneratedAsset, ...] = ()
    error: str | None = Field(default=None, max_length=500)


class DreamExport(_Frozen):
    """Export complet des rêves d'un utilisateur (portabilité, art. 20 RGPD)."""

    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    exported_at: datetime = Field(default_factory=_now)
    dreams: tuple[Dream, ...]
