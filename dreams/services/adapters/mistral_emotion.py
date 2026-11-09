"""Émotion par Mistral Small à sortie JSON : premier repli si Hugging Face échoue."""

from __future__ import annotations

from decimal import Decimal

import httpx
from django.conf import settings
from pydantic import BaseModel, ConfigDict, Field

from dreams.emotions import Emotion
from dreams.models import ApiCall
from dreams.services.adapters.mistral_chat import TIMEOUT, chat_json
from dreams.services.http import CallContext
from dreams.services.ports import Caller, EmotionResult

SYSTEM = """\
Tu reçois la transcription d'un rêve raconté au réveil, en français.
Indique l'émotion dominante du récit parmi la liste autorisée, en te fondant sur le seul texte,
et ta confiance entre 0 et 1. N'interprète pas le rêve, ne donne aucun avis psychologique.
"""


class EmotionOutput(BaseModel):
    """Sortie attendue du modèle."""

    model_config = ConfigDict(extra="forbid")

    emotion: Emotion
    confidence: float = Field(ge=0.0, le=1.0)


class MistralEmotionClassifier:
    """Classification par LLM, validée par schéma."""

    provider = "mistral"

    def __init__(self, client: httpx.Client | None = None, model: str | None = None) -> None:
        """Prépare l'adapter.

        Args:
            client: Client HTTP (injecté par les tests).
            model: Modèle ; ``MISTRAL_LLM_MODEL`` par défaut.
        """
        self.client = client or httpx.Client(timeout=TIMEOUT)
        self.model = model or settings.MISTRAL_LLM_MODEL

    def classify(self, text: str, caller: Caller) -> EmotionResult:
        """Classe le texte.

        Args:
            text: Transcription.
            caller: Contexte de journalisation.

        Returns:
            L'émotion retenue par le modèle.
        """
        ctx = CallContext(ApiCall.Step.EMOTION, self.provider, self.model, caller.dream_id, caller.user_id)
        out = chat_json(self.client, ctx, system=SYSTEM, user=text, schema=EmotionOutput, estimated_tokens=400)
        return EmotionResult(
            out.emotion, Decimal(str(out.confidence)).quantize(Decimal("0.01")), self.provider, self.model
        )
