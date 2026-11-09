"""Ports (interfaces) des services d'IA. L'UI et le pipeline ne connaissent que ces types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from dreamsynth.domain.emotion import Emotion
from dreamsynth.services.dream_analysis import DreamAnalysis


@dataclass(frozen=True)
class TranscriptionResult:
    """Sortie d'un `Transcriber`."""

    text: str
    provider: str
    model: str


@dataclass(frozen=True)
class ImageResult:
    """Sortie d'un `ImageGenerator` : URI de l'image et provenance."""

    uri: str
    provider: str
    model: str


class Transcriber(Protocol):
    """Audio → texte (ADR-002)."""

    def transcribe(self, audio: bytes, filename: str) -> TranscriptionResult:
        """Transcrit un audio en français."""
        ...


class DreamAnalyzer(Protocol):
    """Texte → titre, prompt visuel, émotion (ADR-001, ADR-003)."""

    def analyze(self, text: str, style: str | None = None) -> DreamAnalysis:
        """Analyse la transcription ; n'utilise jamais l'audio."""
        ...


class ImageGenerator(Protocol):
    """Prompt visuel → image (ADR-004)."""

    def generate(self, prompt: str) -> ImageResult:
        """Génère une image à partir du prompt reformulé."""
        ...


class AmbianceLibrary(Protocol):
    """Émotion → boucle d'ambiance (ADR-005)."""

    def for_emotion(self, emotion: Emotion) -> str:
        """URI de la boucle associée à l'émotion."""
        ...


@dataclass(frozen=True)
class Services:
    """Ensemble des adapters injectés dans le pipeline."""

    transcriber: Transcriber
    analyzer: DreamAnalyzer
    image: ImageGenerator
    ambiance: AmbianceLibrary
