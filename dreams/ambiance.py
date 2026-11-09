"""Ambiance sonore associée à l'émotion d'un rêve (US-13, ADR-005).

Bonus **non génératif**, assumé : six boucles de 12 s synthétisées par ffmpeg
(``scripts/make_ambiances.py``, aucun échantillon tiers, diffusables sans restriction),
une par émotion. Aucun appel API, aucun coût, aucune donnée du rêve transmise.
"""

from __future__ import annotations

from django.templatetags.static import static

from dreams.emotions import Emotion

DESCRIPTIONS: dict[str, str] = {
    Emotion.HEUREUX: "accord majeur lumineux, légère pulsation",
    Emotion.SEREIN: "souffle doux et note grave tenue",
    Emotion.NEUTRE: "bruit brun feutré",
    Emotion.ETRANGE: "notes vibrantes et déphasées",
    Emotion.MELANCOLIQUE: "accord mineur voilé, lent",
    Emotion.STRESSANT: "grave sourd et souffle aigu haché",
}


def ambiance_for(emotion: str | None) -> dict[str, str] | None:
    """Boucle d'ambiance d'une émotion.

    Args:
        emotion: Valeur de :class:`Emotion`, ou ``None``.

    Returns:
        ``{"url", "description"}``, ou ``None`` si l'émotion est inconnue.
    """
    if emotion not in DESCRIPTIONS:
        return None
    return {"url": static(f"audio/ambiance/{emotion}.mp3"), "description": DESCRIPTIONS[emotion]}
