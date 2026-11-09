"""Requêtes du tableau de bord, toujours restreintes à l'utilisateur connecté."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from django.db.models import Prefetch, QuerySet
from django.utils import timezone

from dreams.models import Dream, EmotionAnalysis, GeneratedAsset


def _start_of(day: date) -> datetime:
    return timezone.make_aware(datetime.combine(day, time.min))


def user_dreams(user_id: int, filters: dict[str, Any] | None = None) -> QuerySet[Dream]:
    """Rêves d'un utilisateur, du plus récent au plus ancien, filtrés.

    Args:
        user_id: Propriétaire.
        filters: Données nettoyées de :class:`dashboard.forms.DreamFilterForm`.

    Returns:
        Le queryset, avec transcription, émotion courante et images préchargées.
    """
    filters = filters or {}
    qs = (
        Dream.objects.filter(user_id=user_id)
        .select_related("transcription")
        .prefetch_related(
            Prefetch("emotions", queryset=EmotionAnalysis.objects.filter(is_current=True), to_attr="current_emotions"),
            Prefetch(
                "assets",
                queryset=GeneratedAsset.objects.filter(
                    kind=GeneratedAsset.Kind.IMAGE, status=GeneratedAsset.Status.OK
                ).order_by("-attempt"),
                to_attr="ok_images",
            ),
        )
        .order_by("-created_at")
    )
    if filters.get("du"):
        qs = qs.filter(created_at__gte=_start_of(filters["du"]))
    if filters.get("au"):
        # Borne incluse : tout le jour de fin, en heure de Paris.
        qs = qs.filter(created_at__lt=_start_of(filters["au"] + timedelta(days=1)))
    if filters.get("humeur"):
        qs = qs.filter(emotions__is_current=True, emotions__emotion__in=filters["humeur"]).distinct()
    return qs
