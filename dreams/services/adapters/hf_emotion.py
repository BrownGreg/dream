"""Émotion par Hugging Face Inference, classification zero-shot multilingue (ADR-008).

Aucun modèle d'émotion à étiquettes fixes n'est documenté pour le français sur HF Inference
(vérifié le 2026-11-09) : on utilise un modèle NLI multilingue en zero-shot avec des
étiquettes françaises. Endpoint et corps de requête relevés dans ``huggingface_hub``
(``https://router.huggingface.co/hf-inference/models/<id>``, ``inputs`` + ``parameters``).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx
from django.conf import settings

from dreams.emotions import Emotion
from dreams.models import ApiCall
from dreams.services.adapters._http import send
from dreams.services.errors import ProviderError
from dreams.services.http import CallContext, resilient_call
from dreams.services.ports import Caller, EmotionResult

TIMEOUT = httpx.Timeout(15.0, connect=5.0)
HYPOTHESIS = "L'ambiance de ce rêve est {}."

# Étiquettes formulées pour l'inférence (NLI), reliées aux 6 émotions du produit.
LABELS: dict[str, str] = {
    "joyeuse": Emotion.HEUREUX,
    "paisible": Emotion.SEREIN,
    "banale": Emotion.NEUTRE,
    "étrange": Emotion.ETRANGE,
    "triste": Emotion.MELANCOLIQUE,
    "angoissante": Emotion.STRESSANT,
}


def _parse(payload: Any) -> tuple[str, float]:
    """Lit la meilleure étiquette, au format liste ``[{label, score}]`` ou ``{labels, scores}``."""
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        best = max(payload, key=lambda item: float(item["score"]))
        return str(best["label"]), float(best["score"])
    if isinstance(payload, dict) and payload.get("labels") and payload.get("scores"):
        return str(payload["labels"][0]), float(payload["scores"][0])
    raise ProviderError("réponse zero-shot inattendue")


class HuggingFaceEmotionClassifier:
    """Zero-shot mDeBERTa (XNLI) sur le texte transcrit."""

    provider = "huggingface"

    def __init__(self, client: httpx.Client | None = None, model: str | None = None) -> None:
        """Prépare l'adapter.

        Args:
            client: Client HTTP (injecté par les tests).
            model: Modèle HF ; ``HF_EMOTION_MODEL`` par défaut.
        """
        self.client = client or httpx.Client(timeout=TIMEOUT)
        self.model = model or settings.HF_EMOTION_MODEL

    def _call(self, text: str) -> tuple[str, float]:
        if not settings.HF_TOKEN:
            raise ProviderError("HF_TOKEN absent", status=401)
        response = send(
            self.client,
            "POST",
            f"{settings.HF_BASE_URL}/models/{self.model}",
            headers={"Authorization": f"Bearer {settings.HF_TOKEN}"},
            json={
                "inputs": text,
                "parameters": {
                    "candidate_labels": list(LABELS),
                    "hypothesis_template": HYPOTHESIS,
                    "multi_label": False,
                },
            },
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError("réponse non JSON", status=response.status_code) from exc
        label, score = _parse(payload)
        if label not in LABELS:
            raise ProviderError("étiquette inconnue")
        return label, score

    def classify(self, text: str, caller: Caller) -> EmotionResult:
        """Classe le texte par inférence zero-shot.

        Args:
            text: Transcription.
            caller: Contexte de journalisation.

        Returns:
            L'émotion la plus probable et son score.
        """
        ctx = CallContext(ApiCall.Step.EMOTION, self.provider, self.model, caller.dream_id, caller.user_id)
        label, score = resilient_call(ctx, lambda: self._call(text), estimated_units=Decimal(1))
        confidence = Decimal(str(score)).quantize(Decimal("0.01"))
        return EmotionResult(LABELS[label], confidence, self.provider, self.model)
