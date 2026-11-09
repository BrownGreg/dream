"""Émotions reconnues, avec leur icône et leur couleur d'affichage."""

from __future__ import annotations

from enum import StrEnum


class Emotion(StrEnum):
    """Émotion dominante d'un rêve, inférée du texte transcrit (jamais de la voix, ADR-001)."""

    HEUREUX = "heureux"
    SEREIN = "serein"
    NEUTRE = "neutre"
    ETRANGE = "étrange"
    MELANCOLIQUE = "mélancolique"
    STRESSANT = "stressant"

    @property
    def icon(self) -> str:
        """Icône affichée à côté du rêve."""
        return _ICONS[self]

    @property
    def color(self) -> str:
        """Couleur hexadécimale associée (contraste AA sur fond blanc pour le texte)."""
        return _COLORS[self]


_ICONS: dict[Emotion, str] = {
    Emotion.HEUREUX: "☀️",
    Emotion.SEREIN: "🌙",
    Emotion.NEUTRE: "☁️",
    Emotion.ETRANGE: "🌀",
    Emotion.MELANCOLIQUE: "🍂",
    Emotion.STRESSANT: "⚡",
}

_COLORS: dict[Emotion, str] = {
    Emotion.HEUREUX: "#946C00",
    Emotion.SEREIN: "#2B6CB0",
    Emotion.NEUTRE: "#4A5568",
    Emotion.ETRANGE: "#6B46C1",
    Emotion.MELANCOLIQUE: "#975A16",
    Emotion.STRESSANT: "#C53030",
}
