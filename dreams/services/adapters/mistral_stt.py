"""Transcription Mistral Voxtral (ADR-002).

API : ``POST /v1/audio/transcriptions`` (multipart ``file``, ``model``, ``language``) ;
la réponse porte ``text`` et ``usage.prompt_audio_seconds`` (durée facturée).
https://docs.mistral.ai/studio/audio/speech-to-text/transcribe-files (consulté le 2026-11-09).
"""

from __future__ import annotations

from decimal import Decimal

import httpx
from django.conf import settings

from dreams.models import ApiCall
from dreams.services.adapters._http import json_body, send
from dreams.services.errors import ProviderError
from dreams.services.http import CallContext, resilient_call
from dreams.services.ports import AudioInput, Caller, Transcript

# Récits ≤ 3 min : la transcription d'un fichier complet tient largement dans 60 s.
TIMEOUT = httpx.Timeout(60.0, connect=5.0)


class MistralTranscriber:
    """Voxtral Mini Transcribe, langue forcée en français."""

    provider = "mistral"

    def __init__(self, client: httpx.Client | None = None, model: str | None = None) -> None:
        """Prépare l'adapter.

        Args:
            client: Client HTTP (injecté par les tests).
            model: Identifiant du modèle ; ``MISTRAL_STT_MODEL`` par défaut.
        """
        self.client = client or httpx.Client(timeout=TIMEOUT)
        self.model = model or settings.MISTRAL_STT_MODEL

    def _call(self, audio: AudioInput) -> dict[str, object]:
        if not settings.MISTRAL_API_KEY:
            raise ProviderError("MISTRAL_API_KEY absente", status=401)
        response = send(
            self.client,
            "POST",
            f"{settings.MISTRAL_BASE_URL}/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.MISTRAL_API_KEY}"},
            files={"file": ("reve.mp3", audio.data, "audio/mpeg")},
            data={"model": self.model, "language": "fr"},
        )
        payload = json_body(response)
        if not str(payload.get("text", "")).strip():
            # Silence ou bruit : rien à rejouer, l'utilisateur doit réenregistrer.
            raise ProviderError("transcription vide", status=response.status_code)
        return payload

    def transcribe(self, audio: AudioInput, caller: Caller) -> Transcript:
        """Transcrit l'enregistrement en français.

        Args:
            audio: Enregistrement MP3.
            caller: Contexte de journalisation.

        Returns:
            Le texte transcrit.
        """
        ctx = CallContext(ApiCall.Step.STT, self.provider, self.model, caller.dream_id, caller.user_id)

        def billed(payload: dict[str, object]) -> Decimal:
            usage = payload.get("usage")
            seconds = usage.get("prompt_audio_seconds") if isinstance(usage, dict) else None
            return Decimal(str(seconds)) / 60 if seconds else audio.duration_s / 60

        payload = resilient_call(
            ctx, lambda: self._call(audio), estimated_units=audio.duration_s / 60, billed_units=billed
        )
        return Transcript(str(payload["text"]).strip(), self.provider, self.model)
