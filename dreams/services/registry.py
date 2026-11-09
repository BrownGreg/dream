"""Choix des adapters selon ``AI_MODE`` (``real`` ou ``fake``)."""

from __future__ import annotations

from django.conf import settings

from dreams.services.adapters.fake import FakeTranscriber
from dreams.services.adapters.mistral_stt import MistralTranscriber
from dreams.services.ports import Transcriber


def transcriber() -> Transcriber:
    """Retourne l'adapter de transcription configuré.

    Returns:
        Voxtral en mode ``real``, la simulation sinon.
    """
    return MistralTranscriber() if settings.AI_MODE == "real" else FakeTranscriber()
