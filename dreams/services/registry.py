"""Choix des adapters selon ``AI_MODE`` (``real`` ou ``fake``)."""

from __future__ import annotations

from django.conf import settings

from dreams.services.adapters.bfl_image import BflImageGenerator
from dreams.services.adapters.fake import FakeEmotionClassifier, FakeImageGenerator, FakePromptBuilder, FakeTranscriber
from dreams.services.adapters.hf_emotion import HuggingFaceEmotionClassifier
from dreams.services.adapters.mistral_emotion import MistralEmotionClassifier
from dreams.services.adapters.mistral_prompt import MistralPromptBuilder
from dreams.services.adapters.mistral_stt import MistralTranscriber
from dreams.services.emotion import FallbackEmotionClassifier
from dreams.services.ports import EmotionClassifier, ImageGenerator, PromptBuilder, Transcriber


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


def prompt_builder() -> PromptBuilder:
    """Retourne l'adapter de rédaction du prompt visuel.

    Returns:
        Mistral Small en mode ``real``, la simulation sinon.
    """
    return MistralPromptBuilder() if settings.AI_MODE == "real" else FakePromptBuilder()


def image_generator() -> ImageGenerator:
    """Retourne l'adapter de génération d'image.

    Returns:
        FLUX.2 [klein] en mode ``real``, la simulation sinon.
    """
    return BflImageGenerator() if settings.AI_MODE == "real" else FakeImageGenerator()
