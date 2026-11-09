"""Adapters Mistral AI mesurés en direct (STT Voxtral, LLM sortie structurée, TTS Voxtral).

Endpoints (docs consultées le 2026-11-02) :
- POST /v1/audio/transcriptions — multipart `file`, `model`, `language`
  https://docs.mistral.ai/studio/audio/speech-to-text/transcribe-files
- POST /v1/chat/completions — `response_format` json_schema
  https://docs.mistral.ai/studio/conversations/structured-output
- POST /v1/audio/speech — JSON `model`, `input`, `voice_id`, `response_format` ;
  réponse JSON, audio en base64 dans `audio_data`
  https://docs.mistral.ai/studio/audio/text-to-speech/generate-speech

Les identifiants de modèle sont surchargeables par variable d'environnement : vérifier
avec `python benchmark/run_latency.py --list-models` avant une campagne.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx

from dreamsynth.services.dream_analysis import SYSTEM_PROMPT, DreamAnalysis
from providers.base import BenchItem, CallResult, Timing, measured, timed_request

BASE_URL = os.environ.get("MISTRAL_BASE_URL", "https://api.mistral.ai")
STT_MODELS = {
    "mistral_voxtral_mini_3": os.environ.get("MISTRAL_STT_MINI", "voxtral-mini-transcribe-3"),
    "mistral_voxtral_small_3": os.environ.get("MISTRAL_STT_SMALL", "voxtral-small-transcribe-3"),
}
LLM_MODEL = os.environ.get("MISTRAL_LLM_MODEL", "mistral-small-2603")
TTS_MODEL = os.environ.get("MISTRAL_TTS_MODEL", "voxtral-mini-tts-3-0")
TTS_VOICE = os.environ.get("MISTRAL_TTS_VOICE", "voice_592")  # « Marie », voix française


def _headers() -> dict[str, str]:
    key = os.environ.get("MISTRAL_API_KEY", "")
    if not key:
        raise RuntimeError("MISTRAL_API_KEY absent : utilisez --mock")
    return {"Authorization": f"Bearer {key}"}


def _failure(key: str, cat: str, item: BenchItem, retries: int, error: str) -> CallResult:
    return CallResult(key, cat, item.item_id, "live", False, 0, 0.0, 0.0, retries, error)


class MistralSTT:
    """Transcription Voxtral (fichier complet, non streamé)."""

    category = "STT"

    def __init__(self, key: str) -> None:
        """Associe la clé de catalogue au modèle Voxtral."""
        self.key = key
        self.model = STT_MODELS[key]

    async def run(self, client: httpx.AsyncClient, item: BenchItem) -> CallResult:
        """Transcrit le fichier audio de l'item."""
        audio = Path(item.audio_path).read_bytes()

        async def call() -> Timing:
            return await timed_request(
                client,
                lambda: client.build_request(
                    "POST",
                    f"{BASE_URL}/v1/audio/transcriptions",
                    headers=_headers(),
                    files={"file": (Path(item.audio_path).name, audio)},
                    data={"model": self.model, "language": "fr"},
                ),
            )

        timing, retries, error = await measured(call)
        if timing is None:
            return _failure(self.key, self.category, item, retries, error)
        ok = timing.status == 200
        payload = json.loads(timing.body) if ok else {}
        return CallResult(
            provider=self.key,
            category=self.category,
            item_id=item.item_id,
            mode="live",
            ok=ok,
            status_code=timing.status,
            ttfb_s=timing.ttfb_s,
            total_s=timing.total_s,
            retries=retries,
            error="" if ok else timing.body[:200].decode(errors="replace"),
            billed_audio_s=float(payload.get("usage", {}).get("prompt_audio_seconds", 0) or 0),
            output_text=str(payload.get("text", "")),
        )


class MistralLLM:
    """Prompt visuel + émotion en sortie structurée (schéma = modèle Pydantic partagé)."""

    category = "LLM"
    key = "mistral_small_4"

    async def run(self, client: httpx.AsyncClient, item: BenchItem) -> CallResult:
        """Analyse le texte de l'item et valide la sortie contre DreamAnalysis."""
        body = {
            "model": LLM_MODEL,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": item.text},
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

        async def call() -> Timing:
            return await timed_request(
                client,
                lambda: client.build_request(
                    "POST", f"{BASE_URL}/v1/chat/completions", headers=_headers(), json=body
                ),
            )

        timing, retries, error = await measured(call)
        if timing is None:
            return _failure(self.key, self.category, item, retries, error)
        ok = timing.status == 200
        usage: dict[str, int] = {}
        content = ""
        valid = False
        if ok:
            payload = json.loads(timing.body)
            usage = payload.get("usage", {})
            content = payload["choices"][0]["message"]["content"]
            try:
                DreamAnalysis.model_validate_json(content)
                valid = True
            except ValueError:
                valid = False
        return CallResult(
            provider=self.key,
            category=self.category,
            item_id=item.item_id,
            mode="live",
            ok=ok and valid,
            status_code=timing.status,
            ttfb_s=timing.ttfb_s,
            total_s=timing.total_s,
            retries=retries,
            error=""
            if ok and valid
            else ("schéma invalide" if ok else timing.body[:200].decode(errors="replace")),
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            output_text=content,
        )


class MistralTTS:
    """Synthèse vocale Voxtral TTS (voix française)."""

    category = "TTS"
    key = "mistral_voxtral_tts_3"

    async def run(self, client: httpx.AsyncClient, item: BenchItem) -> CallResult:
        """Synthétise le texte de l'item."""
        body = {
            "model": TTS_MODEL,
            "input": item.text,
            "voice_id": TTS_VOICE,
            "response_format": "mp3",
        }

        async def call() -> Timing:
            return await timed_request(
                client,
                lambda: client.build_request(
                    "POST", f"{BASE_URL}/v1/audio/speech", headers=_headers(), json=body
                ),
            )

        timing, retries, error = await measured(call)
        if timing is None:
            return _failure(self.key, self.category, item, retries, error)
        ok = timing.status == 200
        has_audio = ok and bool(json.loads(timing.body).get("audio_data"))
        return CallResult(
            provider=self.key,
            category=self.category,
            item_id=item.item_id,
            mode="live",
            ok=has_audio,
            status_code=timing.status,
            ttfb_s=timing.ttfb_s,
            total_s=timing.total_s,
            retries=retries,
            error="" if has_audio else timing.body[:200].decode(errors="replace"),
            output_chars=len(item.text),
        )


async def list_models(client: httpx.AsyncClient) -> list[str]:
    """Liste les identifiants de modèles accessibles avec la clé (vérification des IDs)."""
    response = await client.get(f"{BASE_URL}/v1/models", headers=_headers())
    response.raise_for_status()
    return sorted(m["id"] for m in response.json().get("data", []))
