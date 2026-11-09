"""Ports : ce que le pipeline attend de chaque fournisseur, sans rien savoir de lui.

Chaque port a un adapter réel et un adapter ``fake`` ; ``registry`` choisit selon ``AI_MODE``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class Caller:
    """Pour qui l'appel est fait ; sert au journal ``ApiCall`` (jamais transmis au fournisseur).

    Attributes:
        dream_id: Rêve traité.
        user_id: Propriétaire du rêve.
    """

    dream_id: UUID | None = None
    user_id: int | None = None


@dataclass(frozen=True)
class AudioInput:
    """Enregistrement prêt à transcrire (déjà validé et converti en MP3).

    Attributes:
        data: Octets MP3.
        duration_s: Durée mesurée par ffprobe.
    """

    data: bytes
    duration_s: Decimal


@dataclass(frozen=True)
class Transcript:
    """Sortie d'un :class:`Transcriber`."""

    text: str
    provider: str
    model: str


class Transcriber(Protocol):
    """Audio → texte français (ADR-002)."""

    def transcribe(self, audio: AudioInput, caller: Caller) -> Transcript:
        """Transcrit l'enregistrement.

        Args:
            audio: Enregistrement MP3.
            caller: Contexte de journalisation.

        Returns:
            Le texte et sa provenance.
        """
        ...
