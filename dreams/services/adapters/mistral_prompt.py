"""Prompt visuel par Mistral Small à sortie JSON (ADR-003).

Le générateur d'image ne reçoit que ce prompt reformulé en anglais, jamais la transcription
(minimisation RGPD). La consigne impose un style onirique, aucun texte dans l'image, aucun
nom propre et un contenu adouci pour les cauchemars.
"""

from __future__ import annotations

import httpx
from django.conf import settings
from pydantic import BaseModel, ConfigDict, Field

from dreams.models import ApiCall
from dreams.services.adapters.mistral_chat import TIMEOUT, chat_json
from dreams.services.http import CallContext
from dreams.services.ports import Caller, VisualPrompt

SYSTEM = """\
Tu reçois la transcription d'un rêve raconté au réveil, en français, et son émotion dominante.
Produis un objet JSON conforme au schéma :
- "title" : un titre de 3 à 6 mots, en français ;
- "visual_prompt" : une description visuelle en anglais, de 60 à 120 mots, pour un générateur d'images.
Règles du prompt visuel :
- style onirique et pictural (lumière douce, couleurs accordées à l'émotion, légère irréalité) ;
- décris lieux, objets, lumière et ambiance ; aucun texte, lettre, chiffre ni logo dans l'image ;
- aucun nom propre, aucune personne réelle reconnaissable, aucun détail identifiant ;
- aucun contenu graphique : ni violence explicite, ni sang, ni nudité ; pour un rêve pénible,
  reste évocateur et symbolique plutôt qu'explicite.
N'interprète pas le rêve et ne donne aucun avis psychologique ou médical.
"""

SOFTER = """
Une première description a été refusée par le filtre de sécurité du générateur d'images.
Rends celle-ci nettement plus douce et plus abstraite : paysage symbolique, aucune personne,
aucune menace visible.
"""


class PromptOutput(BaseModel):
    """Sortie attendue du modèle."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=80)
    visual_prompt: str = Field(min_length=20, max_length=1200)


class MistralPromptBuilder:
    """Rédaction du titre et du prompt visuel par LLM."""

    provider = "mistral"

    def __init__(self, client: httpx.Client | None = None, model: str | None = None) -> None:
        """Prépare l'adapter.

        Args:
            client: Client HTTP (injecté par les tests).
            model: Modèle ; ``MISTRAL_LLM_MODEL`` par défaut.
        """
        self.client = client or httpx.Client(timeout=TIMEOUT)
        self.model = model or settings.MISTRAL_LLM_MODEL

    def build(self, text: str, emotion: str, caller: Caller, *, softer: bool = False) -> VisualPrompt:
        """Rédige le titre et le prompt visuel.

        Args:
            text: Transcription.
            emotion: Émotion retenue.
            caller: Contexte de journalisation.
            softer: Reformulation plus douce après un refus de sécurité.

        Returns:
            Le titre et le prompt.
        """
        ctx = CallContext(ApiCall.Step.PROMPT, self.provider, self.model, caller.dream_id, caller.user_id)
        out = chat_json(
            self.client,
            ctx,
            system=SYSTEM + (SOFTER if softer else ""),
            user=f"Émotion dominante : {emotion}\n\nRécit :\n{text}",
            schema=PromptOutput,
            estimated_tokens=900,
        )
        return VisualPrompt(out.title.strip(), out.visual_prompt.strip(), self.provider, self.model)
