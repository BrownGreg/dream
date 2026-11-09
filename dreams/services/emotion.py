"""Chaîne de repli de l'émotion : Hugging Face → Mistral → lexique local (ADR-008)."""

from __future__ import annotations

from collections.abc import Sequence

import structlog

from dreams.services.adapters.lexicon import LexiconEmotionClassifier
from dreams.services.errors import AIServiceError
from dreams.services.ports import Caller, EmotionClassifier, EmotionResult

log = structlog.get_logger(__name__)


class FallbackEmotionClassifier:
    """Essaie chaque classifieur dans l'ordre ; le lexique final ne peut pas échouer."""

    def __init__(self, chain: Sequence[EmotionClassifier]) -> None:
        """Construit la chaîne.

        Args:
            chain: Classifieurs à essayer avant le lexique, du préféré au moins préféré.
        """
        self.chain = [*chain, LexiconEmotionClassifier()]

    def classify(self, text: str, caller: Caller) -> EmotionResult:
        """Retourne la première réponse obtenue.

        Args:
            text: Transcription.
            caller: Contexte de journalisation.

        Returns:
            L'émotion du premier classifieur qui répond.
        """
        for classifier in self.chain[:-1]:
            try:
                return classifier.classify(text, caller)
            except AIServiceError as exc:
                # Budget épuisé, fournisseur en panne, clé absente : on passe au suivant.
                log.warning(
                    "emotion_fallback",
                    failed=type(classifier).__name__,
                    error=exc.code,
                    dream_id=str(caller.dream_id) if caller.dream_id else None,
                )
        return self.chain[-1].classify(text, caller)
