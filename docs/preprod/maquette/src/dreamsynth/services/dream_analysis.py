"""Contrat de l'étape LLM : réécriture du récit en prompt visuel + émotion (ADR-003).

Le même prompt système et le même schéma servent au benchmark et à l'application.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from dreamsynth.domain.emotion import Emotion

SYSTEM_PROMPT = """\
Tu reçois la transcription d'un rêve raconté au réveil, en français.
Produis un objet JSON conforme au schéma fourni :
- "title" : un titre de 3 à 6 mots en français ;
- "visual_prompt" : une description visuelle en anglais (60 à 120 mots) pour un générateur
  d'images ; décris lieux, objets, lumière et ambiance ; n'inclus ni nom propre de personne
  réelle, ni donnée identifiante, ni contenu graphique (violence, nudité) — reste
  évocateur et non explicite pour les rêves pénibles ;
- "emotion" : l'émotion dominante parmi la liste autorisée, inférée du seul texte ;
- "confidence" : ta confiance entre 0 et 1.
N'interprète pas le rêve, ne formule aucun avis psychologique ou médical.
"""


class DreamAnalysis(BaseModel):
    """Sortie structurée de l'étape LLM."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=80)
    visual_prompt: str = Field(min_length=10, max_length=1200)
    emotion: Emotion
    confidence: float = Field(ge=0.0, le=1.0)
