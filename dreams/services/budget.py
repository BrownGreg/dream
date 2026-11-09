"""Coupe-circuit budgétaire et quota quotidien par utilisateur (ADR-009)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from dreams.models import ApiCall, Dream
from dreams.services.errors import BudgetExceededError, QuotaExceededError


@dataclass(frozen=True)
class BudgetStatus:
    """État du budget API, affiché sur ``/ops``.

    Attributes:
        spent_usd: Coût cumulé estimé, en dollars.
        spent_eur: Même coût converti avec ``AI_USD_EUR_RATE``.
        limit_eur: Seuil du coupe-circuit.
        ratio: Part du seuil consommée (0 à 1 et plus).
        alert: Seuil d'alerte franchi.
        exceeded: Coupe-circuit déclenché.
    """

    spent_usd: Decimal
    spent_eur: Decimal
    limit_eur: Decimal
    ratio: Decimal
    alert: bool
    exceeded: bool


def _rate() -> Decimal:
    return Decimal(str(settings.AI_USD_EUR_RATE))


def budget_status() -> BudgetStatus:
    """Calcule l'état du budget depuis le journal ``ApiCall``.

    Returns:
        Le coût cumulé et sa position par rapport au coupe-circuit.
    """
    spent_usd = ApiCall.objects.aggregate(total=Sum("cost_usd"))["total"] or Decimal(0)
    spent_eur = (spent_usd * _rate()).quantize(Decimal("0.0001"))
    limit = Decimal(str(settings.AI_BUDGET_EUR))
    ratio = (spent_eur / limit).quantize(Decimal("0.0001")) if limit else Decimal(1)
    return BudgetStatus(
        spent_usd=spent_usd,
        spent_eur=spent_eur,
        limit_eur=limit,
        ratio=ratio,
        alert=ratio >= Decimal(str(settings.AI_BUDGET_ALERT_RATIO)),
        exceeded=spent_eur >= limit,
    )


def ensure_budget(next_cost_usd: Decimal = Decimal(0)) -> None:
    """Refuse un appel payant qui ferait dépasser le coupe-circuit.

    Args:
        next_cost_usd: Coût estimé de l'appel envisagé.

    Raises:
        BudgetExceededError: Si le coût cumulé plus cet appel atteint ``AI_BUDGET_EUR``.
    """
    status = budget_status()
    # « Déjà atteint » doit bloquer aussi un appel estimé gratuit (prix NON PUBLIÉ, délai dépassé…).
    if status.exceeded or status.spent_eur + next_cost_usd * _rate() > status.limit_eur:
        raise BudgetExceededError(f"budget atteint : {status.spent_eur} € sur {status.limit_eur} €")


def quota_reset_at(now: datetime | None = None) -> datetime:
    """Prochaine remise à zéro du quota : minuit, heure de Paris.

    Args:
        now: Instant de référence (maintenant par défaut).

    Returns:
        Le prochain minuit local, avec fuseau.
    """
    local = timezone.localtime(now or timezone.now())
    return (local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def ensure_user_quota(user_id: int, now: datetime | None = None) -> None:
    """Refuse un nouveau rêve au-delà de ``AI_USER_DAILY_DREAMS`` par jour.

    Args:
        user_id: Identifiant de l'utilisateur.
        now: Instant de référence (maintenant par défaut).

    Raises:
        QuotaExceededError: Si le quota du jour est atteint.
    """
    reset = quota_reset_at(now)
    start = reset - timedelta(days=1)
    count = Dream.objects.filter(user_id=user_id, created_at__gte=start, created_at__lt=reset).count()
    if count >= settings.AI_USER_DAILY_DREAMS:
        raise QuotaExceededError(reset)
