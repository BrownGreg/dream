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
from dreams.services.ports import AudioInput, Caller, EmotionResult, GeneratedImage, Transcript, VisualPrompt

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


class FakePromptBuilder:
    """Titre tiré des premiers mots du récit, prompt générique accordé à l'émotion."""

    provider = "fake"
    model = "fake-prompt"

    def build(self, text: str, emotion: str, caller: Caller, *, softer: bool = False) -> VisualPrompt:
        """Simule la rédaction du prompt.

        Args:
            text: Transcription.
            emotion: Émotion retenue.
            caller: Contexte de journalisation.
            softer: Variante adoucie.

        Returns:
            Un titre et un prompt déterministes.
        """
        ctx = CallContext(ApiCall.Step.PROMPT, self.provider, self.model, caller.dream_id, caller.user_id)

        def call() -> VisualPrompt:
            simulate(ApiCall.Step.PROMPT)
            words = text.replace(",", " ").replace(".", " ").split()
            title = " ".join(words[2:7]).capitalize() or "Rêve sans titre"
            mood = "abstract soft landscape" if softer else f"dreamlike {emotion} scene"
            prompt = f"A {mood}, painterly, soft light, no text, no people, gentle colors."
            return VisualPrompt(title, prompt, self.provider, self.model)

        return resilient_call(ctx, call, estimated_units=Decimal(0))


class FakeImageGenerator:
    """Image SVG abstraite et déterministe : dégradé et cercles dérivés du prompt."""

    provider = "fake"
    model = "fake-image"

    def generate(self, prompt: str, caller: Caller) -> GeneratedImage:
        """Simule une génération d'image.

        Args:
            prompt: Prompt visuel.
            caller: Contexte de journalisation.

        Returns:
            Une image SVG 1024 x 1024.
        """
        ctx = CallContext(ApiCall.Step.IMAGE, self.provider, self.model, caller.dream_id, caller.user_id)

        def call() -> GeneratedImage:
            simulate(ApiCall.Step.IMAGE)
            digest = hashlib.sha256(prompt.encode()).hexdigest()
            hue = int(digest[:2], 16) * 360 // 256
            circles = "".join(
                f'<circle cx="{int(digest[i : i + 2], 16) * 4}" cy="{int(digest[i + 2 : i + 4], 16) * 4}" '
                f'r="{40 + int(digest[i + 4], 16) * 8}" fill="hsl({(hue + i * 9) % 360} 70% 75%)" opacity="0.45"/>'
                for i in range(6, 42, 6)
            )
            svg = (
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">'
                f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
                f'<stop offset="0" stop-color="hsl({hue} 55% 30%)"/>'
                f'<stop offset="1" stop-color="hsl({(hue + 60) % 360} 60% 12%)"/></linearGradient></defs>'
                f'<rect width="1024" height="1024" fill="url(#g)"/>{circles}</svg>'
            )
            return GeneratedImage(svg.encode(), "svg", self.provider, self.model)

        return resilient_call(ctx, call, estimated_units=Decimal(1))
