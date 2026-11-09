"""Adapters simulés : tests, CI, test de charge et démonstration hors-ligne (``AI_MODE=fake``).

Ils passent par le client résilient comme les vrais (lignes ``ApiCall`` à coût nul), ce qui
rend la page ``/ops`` et le test de charge représentatifs. ``AI_FAKE_LATENCY_MS`` simule la
latence ; ``AI_FAKE_FAIL_STEPS`` (ex. ``image,stt``) simule une panne de fournisseur.
"""

from __future__ import annotations

import hashlib
import time
from decimal import Decimal

from django.conf import settings

from dreams.models import ApiCall
from dreams.services.adapters.lexicon import LexiconEmotionClassifier
from dreams.services.errors import ProviderError
from dreams.services.http import CallContext, resilient_call
from dreams.services.ports import AudioInput, Caller, EmotionResult, Transcript

# Récits synthétiques (corpus du bloc 1), jamais de vrais rêves.
FAKE_DREAMS: tuple[str, ...] = (
    "Je marchais dans une forêt de lampes allumées, l'air sentait la pluie chaude et je riais avec des amis "
    "d'enfance. Tout était lumineux et léger.",
    "J'étais en retard pour un examen, les couloirs de l'école s'allongeaient sans fin et la porte de la salle "
    "reculait chaque fois que je m'approchais.",
    "Je flottais au-dessus d'un lac immobile au lever du jour. Il n'y avait aucun bruit, seulement une brume "
    "rose et des oiseaux très lents.",
    "Une baleine traversait le salon de mes grands-parents en chantant, et personne ne semblait surpris. "
    "Les murs étaient faits de papier à musique.",
    "Je cherchais une maison qui n'existe plus. Les rues de mon ancien quartier étaient vides et les volets "
    "fermés, j'avais une impression de perte.",
)


def simulate(step: str) -> None:
    """Applique la latence et la panne simulées configurées pour une étape.

    Args:
        step: Valeur de ``ApiCall.Step``.

    Raises:
        ProviderError: Si l'étape figure dans ``AI_FAKE_FAIL_STEPS`` (erreur 503, passagère).
    """
    if settings.AI_FAKE_LATENCY_MS:
        time.sleep(settings.AI_FAKE_LATENCY_MS / 1000)
    if step in settings.AI_FAKE_FAIL_STEPS:
        raise ProviderError.from_status(503, f"panne simulée ({step})")


def pick(data: bytes | str, options: tuple[str, ...]) -> str:
    """Choisit une option de façon déterministe à partir d'une empreinte.

    Args:
        data: Contenu dont l'empreinte détermine le choix.
        options: Options possibles.

    Returns:
        Toujours la même option pour le même contenu.
    """
    raw = data.encode() if isinstance(data, str) else data
    return options[int(hashlib.sha256(raw).hexdigest(), 16) % len(options)]


class FakeTranscriber:
    """Renvoie un récit synthétique, toujours le même pour un même enregistrement."""

    provider = "fake"
    model = "fake-stt"

    def transcribe(self, audio: AudioInput, caller: Caller) -> Transcript:
        """Simule une transcription.

        Args:
            audio: Enregistrement.
            caller: Contexte de journalisation.

        Returns:
            Un récit du corpus synthétique.
        """
        ctx = CallContext(ApiCall.Step.STT, self.provider, self.model, caller.dream_id, caller.user_id)

        def call() -> str:
            simulate(ApiCall.Step.STT)
            return pick(audio.data, FAKE_DREAMS)

        text = resilient_call(ctx, call, estimated_units=audio.duration_s / 60 if audio.duration_s else Decimal(0))
        return Transcript(text, self.provider, self.model)


class FakeEmotionClassifier:
    """Simule le classifieur HF : s'appuie sur le lexique, avec une confiance plus élevée."""

    provider = "fake"
    model = "fake-emotion"

    def classify(self, text: str, caller: Caller) -> EmotionResult:
        """Simule une classification.

        Args:
            text: Transcription.
            caller: Contexte de journalisation.

        Returns:
            L'émotion du lexique, confiance 0,8.
        """
        ctx = CallContext(ApiCall.Step.EMOTION, self.provider, self.model, caller.dream_id, caller.user_id)

        def call() -> str:
            simulate(ApiCall.Step.EMOTION)
            return LexiconEmotionClassifier().classify(text, caller).emotion

        emotion = resilient_call(ctx, call, estimated_units=Decimal(1))
        return EmotionResult(emotion, Decimal("0.80"), self.provider, self.model)
