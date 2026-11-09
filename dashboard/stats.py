"""Statistiques personnelles du tableau de bord (US-16), calculées en base.

Toutes les agrégations portent sur l'émotion **courante** de chaque rêve (après une
éventuelle correction par l'utilisateur) et sur les seuls rêves de l'utilisateur.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.db.models import Count
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils import timezone

from dreams.emotions import Emotion
from dreams.models import Dream, EmotionAnalysis

PERIODS: dict[str, int] = {"30": 30, "90": 90, "365": 365}
DEFAULT_PERIOD = "90"
MONTHS_FR = ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc.")


@dataclass(frozen=True)
class Stats:
    """Résultat prêt à afficher.

    Attributes:
        period_days: Durée de la période analysée.
        total: Rêves racontés sur la période.
        per_week: Moyenne de rêves par semaine sur la période.
        dominant: Émotion la plus fréquente (``None`` si aucune).
        weeks: ``[(lundi, nombre de rêves)]`` sur la période, semaines vides comprises.
        distribution: ``[(émotion, nombre)]`` du plus au moins fréquent, sans les zéros.
        months: Libellés des 12 derniers mois.
        evolution: ``{émotion: [nombre par mois]}`` sur les 12 derniers mois.
    """

    period_days: int
    total: int
    per_week: float
    dominant: str | None
    weeks: list[tuple[date, int]]
    distribution: list[tuple[str, int]]
    months: list[str]
    evolution: dict[str, list[int]]


def _tz() -> ZoneInfo:
    return ZoneInfo(timezone.get_current_timezone_name())


def _monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _month_starts(today: date, count: int = 12) -> list[date]:
    year, month = today.year, today.month
    starts = []
    for _ in range(count):
        starts.append(date(year, month, 1))
        year, month = (year, month - 1) if month > 1 else (year - 1, 12)
    return starts[::-1]


def compute(user_id: int, period: str = DEFAULT_PERIOD, now: datetime | None = None) -> Stats:
    """Calcule les statistiques d'un utilisateur.

    Args:
        user_id: Propriétaire des rêves.
        period: Clé de :data:`PERIODS` (une clé inconnue retombe sur la valeur par défaut).
        now: Instant de référence (maintenant par défaut).

    Returns:
        Les statistiques de la période et l'évolution sur 12 mois.
    """
    tz = _tz()
    now = timezone.localtime(now or timezone.now(), tz)
    days = PERIODS.get(period, PERIODS[DEFAULT_PERIOD])
    start = now - timedelta(days=days)
    dreams = Dream.objects.filter(user_id=user_id)
    in_period = dreams.filter(created_at__gte=start)

    total = in_period.count()
    weekly = {
        row["week"].date() if isinstance(row["week"], datetime) else row["week"]: row["n"]
        for row in in_period.annotate(week=TruncWeek("created_at", tzinfo=tz)).values("week").annotate(n=Count("id"))
    }
    weeks: list[tuple[date, int]] = []
    cursor = _monday(start.date())
    while cursor <= now.date():
        weeks.append((cursor, weekly.get(cursor, 0)))
        cursor += timedelta(days=7)

    current = EmotionAnalysis.objects.filter(dream__user_id=user_id, is_current=True)
    counts = {
        row["emotion"]: row["n"]
        for row in current.filter(dream__created_at__gte=start).values("emotion").annotate(n=Count("id"))
    }
    order = [value for value, _ in Emotion.choices]
    distribution = sorted(((e, n) for e, n in counts.items() if n), key=lambda item: (-item[1], order.index(item[0])))

    month_starts = _month_starts(now.date())
    first = timezone.make_aware(datetime.combine(month_starts[0], datetime.min.time()), tz)
    monthly = (
        current.filter(dream__created_at__gte=first)
        .annotate(month=TruncMonth("dream__created_at", tzinfo=tz))
        .values("month", "emotion")
        .annotate(n=Count("id"))
    )
    evolution = {value: [0] * len(month_starts) for value in order}
    index = {m: i for i, m in enumerate(month_starts)}
    for row in monthly:
        month = row["month"].date() if isinstance(row["month"], datetime) else row["month"]
        evolution[row["emotion"]][index[month]] = row["n"]

    return Stats(
        period_days=days,
        total=total,
        per_week=round(total / (days / 7), 1),
        dominant=distribution[0][0] if distribution else None,
        weeks=weeks,
        distribution=distribution,
        months=[f"{MONTHS_FR[m.month - 1]} {m.year % 100:02d}" for m in month_starts],
        evolution=evolution,
    )
