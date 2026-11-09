"""Verrou par rêve, pour qu'un même rêve ne soit jamais traité deux fois en parallèle.

PostgreSQL : verrou consultatif de session (``pg_try_advisory_lock``), non transactionnel,
donc compatible avec les lignes ``ApiCall`` écrites au fil de l'eau (une transaction longue
les ferait disparaître en cas de plantage). Autres bases (SQLite des tests) : pas de verrou.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from django.db import connection


def _key(dream_id: UUID) -> int:
    # Les 63 bits de poids faible de l'UUID donnent une clé bigint signée positive.
    return dream_id.int & 0x7FFF_FFFF_FFFF_FFFF


@contextmanager
def dream_lock(dream_id: UUID) -> Iterator[bool]:
    """Tente de prendre le verrou du rêve sans attendre.

    Args:
        dream_id: Rêve à verrouiller.

    Yields:
        ``True`` si le verrou est pris (ou inutile), ``False`` si un autre worker traite déjà ce rêve.
    """
    if connection.vendor != "postgresql":
        yield True
        return
    key = _key(dream_id)
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [key])
        acquired = bool(cursor.fetchone()[0])
    try:
        yield acquired
    finally:
        if acquired:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [key])
