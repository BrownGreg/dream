"""Ports : ce que le pipeline attend de chaque fournisseur, sans rien savoir de lui.

Chaque port a un adapter réel et un adapter ``fake`` ; ``registry`` choisit selon ``AI_MODE``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class Caller:
    """Pour qui l'appel est fait ; sert au journal ``ApiCall`` (jamais transmis au fournisseur).

    Attributes:
        dream_id: Rêve traité.
        user_id: Propriétaire du rêve.
    """

    dream_id: UUID | None = None
    user_id: int | None = None


@dataclass(frozen=True)
class AudioInput:
    """Enregistrement prêt à transcrire (déjà validé et converti en MP3).

    Attributes:
        data: Octets MP3.
        duration_s: Durée mesurée par ffprobe.
    """

    data: bytes
    duration_s: Decimal


@dataclass(frozen=True)
class Transcript:
    """Sortie d'un :class:`Transcriber`."""

    text: str
    provider: str
    model: str


class Transcriber(Protocol):
    """Audio → texte français (ADR-002)."""

    def transcribe(self, audio: AudioInput, caller: Caller) -> Transcript:
        """Transcrit l'enregistrement.

        Args:
            audio: Enregistrement MP3.
            caller: Contexte de journalisation.

        Returns:
            Le texte et sa provenance.
        """
        ...


@dataclass(frozen=True)
class EmotionResult:
    """Sortie d'un :class:`EmotionClassifier`.

    Attributes:
        emotion: Valeur de :class:`dreams.emotions.Emotion`.
        confidence: Score entre 0 et 1, ou ``None`` si la méthode n'en produit pas.
        provider: Fournisseur ou ``local`` (lexique).
        model: Modèle ou ressource utilisée.
    """

    emotion: str
    confidence: Decimal | None
    provider: str
    model: str


class EmotionClassifier(Protocol):
    """Texte transcrit → émotion dominante ; jamais à partir de la voix (ADR-001)."""

    def classify(self, text: str, caller: Caller) -> EmotionResult:
        """Classe le texte du rêve.

        Args:
            text: Transcription.
            caller: Contexte de journalisation.

        Returns:
            L'émotion dominante et sa confiance.
        """
        ...


@dataclass(frozen=True)
class VisualPrompt:
    """Sortie d'un :class:`PromptBuilder`.

    Attributes:
        title: Titre court en français (3 à 6 mots).
        prompt: Description visuelle en anglais, sans nom ni détail identifiant.
        provider: Fournisseur.
        model: Modèle.
    """

    title: str
    prompt: str
    provider: str
    model: str


class PromptBuilder(Protocol):
    """Récit → titre et prompt visuel sûr (ADR-003) ; le générateur d'image ne voit jamais le récit."""

    def build(self, text: str, emotion: str, caller: Caller, *, softer: bool = False) -> VisualPrompt:
        """Rédige le prompt visuel.

        Args:
            text: Transcription.
            emotion: Émotion retenue, pour accorder l'ambiance.
            caller: Contexte de journalisation.
            softer: Reformulation plus douce, après un refus du filtre de sécurité.

        Returns:
            Le titre et le prompt.
        """
        ...


@dataclass(frozen=True)
class GeneratedImage:
    """Image téléchargée chez le fournisseur, prête à stocker chez nous.

    Attributes:
        data: Octets de l'image.
        extension: Extension du fichier (``jpg``, ``png``, ``webp``).
        provider: Fournisseur.
        model: Modèle.
    """

    data: bytes
    extension: str
    provider: str
    model: str


class ImageGenerator(Protocol):
    """Prompt visuel → image (ADR-004)."""

    def generate(self, prompt: str, caller: Caller) -> GeneratedImage:
        """Génère et télécharge l'image.

        Args:
            prompt: Prompt visuel reformulé.
            caller: Contexte de journalisation.

        Returns:
            L'image.

        Raises:
            SafetyRejectionError: Le filtre du fournisseur a refusé le prompt ou l'image.
        """
        ...
