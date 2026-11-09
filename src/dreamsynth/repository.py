"""Historique des rêves de la maquette (en mémoire, stocké dans `st.session_state`).

Préfigure le dépôt PostgreSQL de la cible : mêmes opérations, mêmes garanties
d'effacement en cascade (EXF-19, EXF-21) et d'export conforme au schéma (EXF-20).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from dreamsynth.domain.emotion import Emotion
from dreamsynth.domain.models import ConsentScope, Dream, DreamExport


@dataclass(frozen=True)
class AuditEntry:
    """Trace d'une action sensible, sans contenu de rêve."""

    action: str
    at: datetime


@dataclass
class DreamRepository:
    """Rêves d'un utilisateur et index des fichiers générés."""

    _dreams: dict[UUID, Dream] = field(default_factory=dict)
    _files: dict[str, UUID] = field(default_factory=dict)
    audit: list[AuditEntry] = field(default_factory=list)
    consents: frozenset[ConsentScope] = frozenset()

    def set_consents(self, scopes: frozenset[ConsentScope]) -> None:
        """Enregistre les consentements courants et trace le changement."""
        self.consents = scopes
        self.audit.append(AuditEntry("consent.update", datetime.now(UTC)))

    def save(self, dream: Dream) -> None:
        """Ajoute ou remplace un rêve et indexe ses fichiers."""
        self._drop_files(dream.id)
        self._dreams[dream.id] = dream
        for asset in dream.assets:
            self._files[asset.uri] = dream.id

    def get(self, dream_id: UUID) -> Dream | None:
        """Rêve par identifiant."""
        return self._dreams.get(dream_id)

    def history(self, emotions: set[Emotion] | None = None) -> list[Dream]:
        """Rêves du plus récent au plus ancien, filtrés par émotion si demandé."""
        dreams = sorted(self._dreams.values(), key=lambda d: d.created_at, reverse=True)
        if emotions:
            dreams = [d for d in dreams if d.emotion and d.emotion.emotion in emotions]
        return dreams

    def files_of(self, dream_id: UUID) -> list[str]:
        """Fichiers encore rattachés à un rêve."""
        return [uri for uri, owner in self._files.items() if owner == dream_id]

    def delete(self, dream_id: UUID) -> bool:
        """Supprime un rêve et tous ses fichiers ; retourne False s'il n'existait pas."""
        if self._dreams.pop(dream_id, None) is None:
            return False
        self._drop_files(dream_id)
        self.audit.append(AuditEntry("dream.delete", datetime.now(UTC)))
        return True

    def delete_all(self) -> None:
        """Suppression du compte : plus aucun rêve, fichier ni consentement ; audit conservé."""
        self._dreams.clear()
        self._files.clear()
        self.consents = frozenset()
        self.audit.append(AuditEntry("account.delete", datetime.now(UTC)))

    def export(self) -> DreamExport:
        """Export complet, conforme à `dream.schema.json` (US-15)."""
        self.audit.append(AuditEntry("export", datetime.now(UTC)))
        return DreamExport(dreams=tuple(self.history()))

    def monthly_emotions(self) -> dict[str, Counter[Emotion]]:
        """Répartition des émotions par mois `AAAA-MM` (US-16), mois croissants."""
        result: dict[str, Counter[Emotion]] = {}
        for dream in sorted(self._dreams.values(), key=lambda d: d.created_at):
            if dream.emotion is None:
                continue
            month = dream.created_at.strftime("%Y-%m")
            result.setdefault(month, Counter())[dream.emotion.emotion] += 1
        return result

    def __len__(self) -> int:
        """Nombre de rêves."""
        return len(self._dreams)

    def _drop_files(self, dream_id: UUID) -> None:
        for uri in self.files_of(dream_id):
            del self._files[uri]
