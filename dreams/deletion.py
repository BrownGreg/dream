"""Suppression définitive d'un rêve et de tous ses fichiers (US-12, RGPD art. 17).

La suppression en cascade de Django efface les lignes, pas les fichiers : ils sont
supprimés explicitement ici, avant les lignes. Le journal ``ApiCall`` garde le coût,
sans lien vers le rêve (``SET NULL``).
"""

from __future__ import annotations

import structlog
from django.db import transaction

from dreams.models import Dream

log = structlog.get_logger(__name__)


def delete_dream(dream: Dream) -> int:
    """Supprime un rêve, son audio, ses images et ses données liées.

    Args:
        dream: Rêve à supprimer.

    Returns:
        Le nombre de fichiers supprimés.
    """
    files = [asset.file for asset in dream.assets.all() if asset.file]
    if dream.audio:
        files.append(dream.audio)
    dream_id = str(dream.id)
    with transaction.atomic():
        for field in files:
            field.delete(save=False)
        dream.delete()
    log.info("dream_deleted", dream_id=dream_id, files=len(files))
    return len(files)
