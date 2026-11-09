"""Choix des adapters selon ``AI_MODE`` (``real`` ou ``fake``)."""

from __future__ import annotations

from django.conf import settings

from dreams.services.adapters.fake import FakeEmotionClassifier, FakeTranscriber
from dreams.services.adapters.hf_emotion import HuggingFaceEmotionClassifier
from dreams.services.adapters.mistral_emotion import MistralEmotionClassifier
from dreams.services.adapters.mistral_stt import MistralTranscriber
from dreams.services.emotion import FallbackEmotionClassifier
from dreams.services.ports import EmotionClassifier, Transcriber


def transcriber() -> Transcriber:
    """Retourne l'adapter de transcription configuré.

    Returns:
        Voxtral en mode ``real``, la simulation sinon.
    """
    return MistralTranscriber() if settings.AI_MODE == "real" else FakeTranscriber()


def emotion_classifier() -> EmotionClassifier:
    """Retourne la chaîne de classification de l'émotion.

    Returns:
        HF → Mistral → lexique en mode ``real`` ; simulation → lexique sinon.
    """
    if settings.AI_MODE == "real":
        return FallbackEmotionClassifier([HuggingFaceEmotionClassifier(), MistralEmotionClassifier()])
    return FallbackEmotionClassifier([FakeEmotionClassifier()])
