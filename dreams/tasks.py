"""Tâches de fond (``django.tasks``, backend base de données, worker ``db_worker``)."""

from __future__ import annotations

from uuid import UUID

from django.tasks import task

from dreams import pipeline


@task()
def process_dream(dream_id: str) -> str:
    """Traite un rêve : transcription, émotion, image.

    Args:
        dream_id: Identifiant du rêve (chaîne : les arguments de tâche sont sérialisés en JSON).

    Returns:
        Le statut final du rêve.
    """
    return pipeline.run(UUID(dream_id))


@task()
def regenerate_image(dream_id: str) -> str:
    """Génère une nouvelle image pour un rêve déjà transcrit (US-07), dans la limite des tentatives.

    Args:
        dream_id: Identifiant du rêve.

    Returns:
        Le statut de la nouvelle tentative.
    """
    return pipeline.regenerate(UUID(dream_id))
