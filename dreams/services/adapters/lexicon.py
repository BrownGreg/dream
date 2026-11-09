"""Dernier repli : lexique émotionnel français, local, gratuit et déterministe.

Lexique **rédigé pour ce projet** (une vingtaine de racines par émotion), et non le lexique
FEEL : il garantit une réponse quand tous les fournisseurs sont indisponibles ou que le
budget est épuisé, sans prétendre à la précision d'un modèle. Sa confiance est plafonnée à 0,5.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal

from dreams.emotions import Emotion
from dreams.services.ports import Caller, EmotionResult

# Racines sans accent : « angoiss » couvre angoisse, angoissé, angoissante…
ROOTS: dict[str, tuple[str, ...]] = {
    Emotion.HEUREUX: (
        "joie",
        "joyeu",
        "heureu",
        "rire",
        "riai",
        "riant",
        "sourir",
        "fete",
        "bonheur",
        "amour",
        "amis",
        "lumineu",
        "soleil",
        "danse",
        "gagn",
        "chant",
        "leger",
        "rigol",
        "content",
        "ravi",
    ),
    Emotion.SEREIN: (
        "calme",
        "paisib",
        "doux",
        "douce",
        "silence",
        "flott",
        "lac",
        "mer ",
        "brume",
        "repos",
        "tranquil",
        "serein",
        "lent",
        "apais",
        "nuage",
        "vent leger",
        "respir",
        "plage",
        "jardin",
        "lever du jour",
    ),
    Emotion.ETRANGE: (
        "bizarre",
        "etrange",
        "absurde",
        "baleine",
        "parl",
        "transform",
        "volai",
        "voler",
        "impossible",
        "invisible",
        "geant",
        "minuscule",
        "surpris",
        "melang",
        "magique",
        "dragon",
        "papier",
        "miroir",
        "sans fin",
        "inconnu",
    ),
    Emotion.MELANCOLIQUE: (
        "triste",
        "pleur",
        "larme",
        "perte",
        "perdu",
        "manque",
        "absent",
        "vide",
        "seul",
        "ancien",
        "disparu",
        "regret",
        "nostalg",
        "adieu",
        "enfance",
        "mort",
        "deuil",
        "gris",
        "ferme",
        "n'existe plus",
    ),
    Emotion.STRESSANT: (
        "peur",
        "angoiss",
        "retard",
        "poursui",
        "fuir",
        "fuyai",
        "tomb",
        "cri",
        "panique",
        "examen",
        "noir",
        "monstre",
        "piege",
        "coince",
        "attaqu",
        "sang",
        "mourir",
        "noy",
        "perdu mes",
        "recul",
    ),
}


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


class LexiconEmotionClassifier:
    """Compte les racines de chaque émotion ; ``neutre`` si aucune n'apparaît."""

    provider = "local"
    model = "lexique-fr-v1"

    def classify(self, text: str, caller: Caller) -> EmotionResult:
        """Classe le texte sans appel réseau.

        Args:
            text: Transcription.
            caller: Contexte (inutilisé : aucun appel externe à journaliser).

        Returns:
            L'émotion la plus représentée, confiance ≤ 0,5.
        """
        normalized = f" {_normalize(text)} "
        scores = {
            emotion: sum(len(re.findall(re.escape(root), normalized)) for root in roots)
            for emotion, roots in ROOTS.items()
        }
        total = sum(scores.values())
        if total == 0:
            return EmotionResult(Emotion.NEUTRE, Decimal("0.30"), self.provider, self.model)
        best = max(scores, key=lambda e: scores[e])
        confidence = min(Decimal("0.50"), Decimal(scores[best]) / Decimal(total) / 2 + Decimal("0.20"))
        return EmotionResult(best, confidence.quantize(Decimal("0.01")), self.provider, self.model)
