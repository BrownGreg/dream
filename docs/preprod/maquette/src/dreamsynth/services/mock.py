"""Adapters simulés de la maquette : déterministes, sans réseau, pannes simulables.

- `MockTranscriber` : transcription fictive choisie par empreinte de l'audio ;
- `KeywordAnalyzer` : émotion par mots-clés (simulée) et prompt visuel gabarit ;
- `PlaceholderImageGenerator` : URL stable et déterministe (picsum.photos, graine = hash du
  prompt) ;
- `LocalAmbianceLibrary` : boucles sonores locales par émotion.
"""

from __future__ import annotations

import hashlib
import time
from enum import StrEnum
from pathlib import Path

from dreamsynth.domain.emotion import Emotion
from dreamsynth.errors import ContentRejectedError, ErrorCode, ServiceTimeoutError
from dreamsynth.errors import ServiceUnavailableError as Unavailable
from dreamsynth.services.dream_analysis import DreamAnalysis
from dreamsynth.services.ports import ImageResult, TranscriptionResult

SAMPLE_DREAMS = (
    "J'étais dans un train qui roulait sous la mer. Des poissons lumineux passaient "
    "derrière les vitres et je n'arrivais pas à savoir où le train allait.",
    "Je marchais dans un couloir sans fin, les portes changeaient de numéro et une alarme "
    "sonnait au loin. Je cherchais quelqu'un sans le trouver.",
    "Je préparais un gâteau aux fraises avec toute ma famille dans une maison au bord de la "
    "mer, le soleil restait couché sur l'eau.",
    "Je revenais dans l'appartement de mon enfance, vide, avec la lumière de fin d'après-midi "
    "sur le parquet.",
)

KEYWORDS: dict[Emotion, tuple[str, ...]] = {
    Emotion.STRESSANT: (
        "tomb",
        "vide",
        "peur",
        "alarme",
        "poursuiv",
        "courais",
        "perdu",
        "sans fin",
        "personne ne",
        "cri",
    ),
    Emotion.MELANCOLIQUE: ("vide,", "enfance", "feuilles mortes", "partir", "absent", "nostalg"),
    Emotion.HEUREUX: ("famille", "gâteau", "rire", "souri", "soleil", "fête", "joie"),
    Emotion.SEREIN: ("calme", "flott", "doux", "silence", "plage", "lumière douce"),
    Emotion.ETRANGE: ("girafe", "pingouin", "à l'envers", "sous la mer", "bizarre", "volant"),
}


class Failure(StrEnum):
    """Pannes simulables depuis la maquette (démonstration des branches d'erreur)."""

    NONE = "none"
    STT_UNAVAILABLE = "stt_unavailable"
    STT_TIMEOUT = "stt_timeout"
    IMAGE_REJECTED = "image_rejected"


class MockTranscriber:
    """Transcription fictive, stable pour un même audio."""

    def __init__(self, failure: Failure = Failure.NONE, latency_s: float = 0.0) -> None:
        """Configure la panne simulée et la latence artificielle."""
        self.failure = failure
        self.latency_s = latency_s

    def transcribe(self, audio: bytes, filename: str) -> TranscriptionResult:
        """Retourne un récit d'exemple choisi par empreinte de l'audio."""
        del filename
        time.sleep(self.latency_s)
        if self.failure is Failure.STT_UNAVAILABLE:
            raise Unavailable(ErrorCode.STT_UNAVAILABLE, "simulé")
        if self.failure is Failure.STT_TIMEOUT:
            raise ServiceTimeoutError(ErrorCode.TIMEOUT, "simulé")
        index = int(hashlib.sha256(audio).hexdigest(), 16) % len(SAMPLE_DREAMS)
        return TranscriptionResult(SAMPLE_DREAMS[index], provider="mock", model="mock-stt")


def classify(text: str) -> tuple[Emotion, float]:
    """Émotion simulée : classe qui totalise le plus de mots-clés, sinon neutre."""
    lowered = text.lower()
    scores = {emo: sum(lowered.count(k) for k in keys) for emo, keys in KEYWORDS.items()}
    best = max(scores, key=lambda e: scores[e])
    if scores[best] == 0:
        return Emotion.NEUTRE, 0.5
    return best, min(0.95, 0.55 + 0.1 * scores[best])


class KeywordAnalyzer:
    """Analyse simulée : même contrat `DreamAnalysis` que l'adapter Mistral."""

    def __init__(self, latency_s: float = 0.0) -> None:
        """Configure la latence artificielle."""
        self.latency_s = latency_s

    def analyze(self, text: str, style: str | None = None) -> DreamAnalysis:
        """Produit un titre, un prompt gabarit et une émotion par mots-clés."""
        time.sleep(self.latency_s)
        emotion, confidence = classify(text)
        words = text.split()
        title = " ".join(words[:5]).rstrip(".,;") or "Rêve sans titre"
        prompt = f"Dreamlike scene, {emotion.value} mood: {text[:300]}"
        if style:
            prompt += f", {style} style"
        return DreamAnalysis(
            title=title[:80],
            visual_prompt=prompt[:1200],
            emotion=emotion,
            confidence=round(confidence, 2),
        )


class PlaceholderImageGenerator:
    """Image placeholder via une URL publique stable (même prompt → même image)."""

    BASE_URL = "https://picsum.photos/seed/{seed}/768/768"

    def __init__(self, failure: Failure = Failure.NONE, latency_s: float = 0.0) -> None:
        """Configure la panne simulée et la latence artificielle."""
        self.failure = failure
        self.latency_s = latency_s
        self.calls = 0

    def generate(self, prompt: str) -> ImageResult:
        """Retourne l'URL déterministe dérivée du hash du prompt."""
        self.calls += 1
        time.sleep(self.latency_s)
        if self.failure is Failure.IMAGE_REJECTED:
            raise ContentRejectedError(ErrorCode.IMAGE_REJECTED_SAFETY, "simulé")
        seed = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        return ImageResult(self.BASE_URL.format(seed=seed), provider="picsum", model="placeholder")


class LocalAmbianceLibrary:
    """Boucles d'ambiance locales : `<dossier>/<émotion>.mp3` (ADR-005)."""

    def __init__(self, directory: Path) -> None:
        """Mémorise le dossier des boucles."""
        self.directory = directory

    def for_emotion(self, emotion: Emotion) -> str:
        """Chemin de la boucle associée à l'émotion."""
        return str(self.directory / f"{emotion.name.lower()}.mp3")
