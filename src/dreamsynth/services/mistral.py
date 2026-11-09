"""Adapters réels Mistral AI (STT Voxtral, LLM à sortie structurée).

Branchés par variable d'environnement. Endpoints et paramètres :
voir benchmark/providers/mistral.py (documentation datée).
"""

from __future__ import annotations

import os

import httpx
from pydantic import ValidationError

from dreamsynth.errors import DreamError, ErrorCode, ServiceTimeoutError
from dreamsynth.errors import ServiceUnavailableError as Unavailable
from dreamsynth.services.dream_analysis import SYSTEM_PROMPT, DreamAnalysis
from dreamsynth.services.ports import TranscriptionResult

BASE_URL = "https://api.mistral.ai"
TIMEOUT = httpx.Timeout(30.0, connect=5.0)


def _api_key() -> str:
    key = os.environ.get("MISTRAL_API_KEY", "")
    if not key:
        raise Unavailable(ErrorCode.STT_UNAVAILABLE, "MISTRAL_API_KEY absent")
    return key


def _post(client: httpx.Client, path: str, code: ErrorCode, **kwargs: object) -> httpx.Response:
    try:
        response = client.post(
            f"{BASE_URL}{path}",
            headers={"Authorization": f"Bearer {_api_key()}"},
            **kwargs,  # type: ignore[arg-type]
        )
    except httpx.TimeoutException as exc:
        raise ServiceTimeoutError(ErrorCode.TIMEOUT, path) from exc
    except httpx.TransportError as exc:
        raise Unavailable(code, repr(exc)) from exc
    if response.status_code >= 400:
        raise Unavailable(code, f"HTTP {response.status_code}")
    return response


class MistralTranscriber:
    """Voxtral Mini Transcribe 3, `language=fr`."""

    def __init__(self, client: httpx.Client | None = None, model: str | None = None) -> None:
        """Injecte un client HTTP (tests) et le modèle à utiliser."""
        self.client = client or httpx.Client(timeout=TIMEOUT)
        self.model = model or os.environ.get("MISTRAL_STT_MINI", "voxtral-mini-transcribe-3")

    def transcribe(self, audio: bytes, filename: str) -> TranscriptionResult:
        """Envoie l'audio à `/v1/audio/transcriptions`."""
        response = _post(
            self.client,
            "/v1/audio/transcriptions",
            ErrorCode.STT_UNAVAILABLE,
            files={"file": (filename, audio)},
            data={"model": self.model, "language": "fr"},
        )
        text = str(response.json().get("text", "")).strip()
        if not text:
            raise Unavailable(ErrorCode.STT_UNAVAILABLE, "transcription vide")
        return TranscriptionResult(text, provider="mistral", model=self.model)


class MistralAnalyzer:
    """Mistral Small 4 avec `response_format` JSON Schema = `DreamAnalysis`."""

    def __init__(self, client: httpx.Client | None = None, model: str | None = None) -> None:
        """Injecte un client HTTP (tests) et le modèle à utiliser."""
        self.client = client or httpx.Client(timeout=TIMEOUT)
        self.model = model or os.environ.get("MISTRAL_LLM_MODEL", "mistral-small-2603")

    def analyze(self, text: str, style: str | None = None) -> DreamAnalysis:
        """Analyse le texte ; un second essai si la sortie ne respecte pas le schéma."""
        user = text if not style else f"{text}\n\nStyle visuel souhaité : {style}"
        body = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "dream_analysis",
                    "schema": DreamAnalysis.model_json_schema(),
                    "strict": True,
                },
            },
        }
        for _ in range(2):
            response = _post(
                self.client, "/v1/chat/completions", ErrorCode.LLM_INVALID_OUTPUT, json=body
            )
            content = response.json()["choices"][0]["message"]["content"]
            try:
                return DreamAnalysis.model_validate_json(content)
            except ValidationError:
                continue
        raise DreamError(ErrorCode.LLM_INVALID_OUTPUT, "sortie non conforme au schéma")
