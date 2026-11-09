"""Émotions reconnues (reprises de la maquette du bloc 1), avec icône et couleur.

Les valeurs stockées sont sans accent pour rester stables dans les URL et les
filtres ; les libellés affichés gardent l'orthographe française.
"""

from django.db import models


class Emotion(models.TextChoices):
    """Émotion dominante d'un rêve, inférée du texte transcrit, jamais de la voix (ADR-001)."""

    HEUREUX = "heureux", "Heureux"
    SEREIN = "serein", "Serein"
    NEUTRE = "neutre", "Neutre"
    ETRANGE = "etrange", "Étrange"
    MELANCOLIQUE = "melancolique", "Mélancolique"
    STRESSANT = "stressant", "Stressant"


ICONS: dict[str, str] = {
    Emotion.HEUREUX: "☀️",
    Emotion.SEREIN: "🌙",
    Emotion.NEUTRE: "☁️",
    Emotion.ETRANGE: "🌀",
    Emotion.MELANCOLIQUE: "🍂",
    Emotion.STRESSANT: "⚡",
}

# Couleurs claires : contraste ≥ 4,5:1 (AA) sur le fond sombre de l'interface (#0b1020).
COLORS: dict[str, str] = {
    Emotion.HEUREUX: "#fcd34d",
    Emotion.SEREIN: "#93c5fd",
    Emotion.NEUTRE: "#cbd5e1",
    Emotion.ETRANGE: "#c4b5fd",
    Emotion.MELANCOLIQUE: "#fdba74",
    Emotion.STRESSANT: "#fca5a5",
}
