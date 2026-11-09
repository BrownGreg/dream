"""Adapter faster-whisper auto-hébergé : mesure réelle, sans clé ni transfert de données.

TTFB = temps jusqu'au premier segment transcrit ; total = transcription complète
(décodage audio exclu, identique pour toutes les options).
Le temps de chargement du modèle est mesuré une fois, à part (`load_s`), et exclu des appels.
Matériel : celui de la machine qui exécute la campagne (consigné dans le CSV).
"""

from __future__ import annotations

import asyncio
import os
import platform
import shutil
import subprocess
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import numpy as np

import httpx

from providers.base import BenchItem, CallResult

MODEL_SIZE = os.environ.get("WHISPER_MODEL", "small")


class LocalWhisper:
    """Transcription faster-whisper sur CPU (int8)."""

    key = "faster_whisper_selfhosted"
    category = "STT"

    def __init__(self) -> None:
        """Charge le modèle et mémorise la durée de chargement."""
        from faster_whisper import WhisperModel

        start = time.perf_counter()
        self.model: Any = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
        self.load_s = time.perf_counter() - start
        self.hardware = f"{platform.processor() or platform.machine()} · {os.cpu_count()} cœurs"

    @staticmethod
    def _decode(path: str) -> np.ndarray[Any, np.dtype[np.float32]]:
        """Décode en PCM 16 kHz mono float32 via ffmpeg (contourne l'API PyAV)."""
        import numpy as np

        ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
        raw = subprocess.run(  # noqa: S603
            [
                ffmpeg,
                "-loglevel",
                "error",
                "-i",
                path,
                "-f",
                "f32le",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-",
            ],
            check=True,
            capture_output=True,
        ).stdout
        return np.frombuffer(raw, dtype=np.float32)

    def _transcribe(self, path: str) -> tuple[float, float, str, float]:
        audio = self._decode(path)
        start = time.perf_counter()
        segments, info = self.model.transcribe(audio, language="fr", beam_size=5)
        first = -1.0
        parts: list[str] = []
        for segment in segments:
            if first < 0:
                first = time.perf_counter() - start
            parts.append(segment.text)
        total = time.perf_counter() - start
        return (
            first if first >= 0 else total,
            total,
            " ".join(p.strip() for p in parts),
            info.duration,
        )

    async def run(self, client: httpx.AsyncClient, item: BenchItem) -> CallResult:
        """Transcrit le fichier audio de l'item dans un thread."""
        del client
        try:
            ttfb, total, text, duration = await asyncio.to_thread(self._transcribe, item.audio_path)
        except Exception as exc:
            return CallResult(
                self.key, self.category, item.item_id, "local", False, 0, 0, 0, 0, repr(exc)
            )
        return CallResult(
            provider=self.key,
            category=self.category,
            item_id=item.item_id,
            mode="local",
            ok=bool(text),
            status_code=200,
            ttfb_s=ttfb,
            total_s=total,
            retries=0,
            billed_audio_s=duration,
            output_text=text,
            extra={"model": MODEL_SIZE, "load_s": self.load_s, "hardware": self.hardware},
        )
